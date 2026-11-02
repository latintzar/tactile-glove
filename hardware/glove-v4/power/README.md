# V4 power and controller circuit

`power-circuit.json` is the numbered-pin source for this subsystem. `build_power.py` regenerates it. The complete cuff source is the parent `electrical/components.json`; the retained tactile circuit supplies the ADC, its 1.8 V regulator and 3.0 V reference reservoir. The current `power-circuit.json` contains 161 numbered part records. The complete V4 electrical source `../electrical/components.json` contains 561 component records, including the ESP32-S3-WROOM-1-N8R8, charger, regulators, USB-C control, single button, RGB indicator and two GPIO expanders.

## Power path

USB VBUS enters two reverse-blocking current-limited paths in parallel. The TPS22950YBHR recovery path uses 19.2 kΩ ±0.1% for its specified 34–66 mA range. The TPS2553DBVR path uses 71.5 kΩ ±0.1%; 30.9 kΩ is switched in parallel for Type-C 1.5/3 A advertisement. Calculated total upper limits, including the recovery path and control current allowance, are 66.37 mA before enumeration, 481.97 mA after enumeration, and 1348.17 mA with high-current advertisement. The low-current branch remains enabled when the high-current branch conducts, because its disabled-output discharge resistor would otherwise load the shared output. USB suspend disables both branches.

TUSB320LAIRWBR operates as a sink in GPIO mode with its internal dead-battery Rd terminations. CC OUT1/OUT2 = HH unattached, HL default, LH 1.5 A, LL 3 A. A physical SN74LVC1G74 latch grants the configured-current state only after firmware confirms USB enumeration. Detach, ESP reset and firmware clear erase that permission. The manufacturer's DCU pin assignment is CLK=1, D=2, /Q=3, GND=4, Q=5, /CLR=6, /PRE=7, VCC=8.

BQ25616RTWR provides switching charging and battery supplement through its power path. VSET floats for 4.2 V; OTG is grounded. Its D+/D− detection pins are isolated from USB data. External current limiters remain authoritative regardless of automatic charger detection. The 562 Ω ±0.1% charge setting gives approximately 1.205 A, bounded to 1.139–1.281 A using the datasheet conditions. The charger uses 1.5 µH XFL4020-152MEC, 10 µF PMID, 4.7 µF REGN, 47 nF bootstrap, 47 µF BAT and two 47 µF SYS capacitors. Its fast-charge timer is 10 h nominal, 8–12 h specified; DPM or thermal regulation halves the timer clock. Earlier 20 h claims for this part are superseded by the current datasheet.

TPS63070RNMR converts VSYS to nominal 3.416 V (`3V3_SYS`) using 327 kΩ/100 kΩ ±0.1% feedback, a 1.5 µH XFL4020 inductor, three 47 µF output capacitors and local 10 µF input/output capacitors. REG_PFM defaults LOW for PWM startup and acquisition. Firmware selects PFM only after camera, SD and analog loads are disabled and the rail settles. A 300 kΩ/100 kΩ divider on EN adds input undervoltage hysteresis. The protected pack and firmware low-voltage policy remain separate protections.

TPS7A2033PDBVR supplies the quiet analog rail. Under the calculated worst supply droop it may leave 3.3 V regulation, while the analog amplifiers retain operating headroom. REF3330 is fed from a separately gated main rail through 10 Ω and 1 µF, preserving its 3.2 V minimum input requirement. The original 6.8 µF tantalum + ceramic reference reservoir remains fitted. Separate PMV16XN/22 Ω paths discharge the reference input and output when analog acquisition is disabled. The analog output has three 47 µF capacitors. PMEG2010ER reverse-discharge diodes protect the reference and analog LDO; the retained ADC LDO keeps its own reverse diode.

ADC DVIO and its local bypass use `3V3_SYS`. Its AVDD remains 1.8 V. The integrated firmware waits for supplies/reference and explicitly calibrates the ADC before acquisition. Firmware drives CNV, SCK and mux controls LOW before analog shutdown.

## Battery, temperature and user controls

The battery source is the Jauch `250480 / LI18650JLS HB 1S2P+PCM+FUSE+2 WIRES 70MM` protected cylindrical 1S2P pack: minimum 6.5 Ah at nominal 3.6 V, nominal envelope 69 × 38 × 20 mm, 100 g, and 10–45 °C charge range. Its supplied two-wire power lead does not expose the internal thermistor. A separate Semitec 103AT-2 NTC is bonded to the pack surface with an insulated thermal attachment and plugs into J_NTC. The direct Micro-Fit battery termination and acceptance procedure are recorded in [battery-harness.md](../procurement/battery-harness.md).

BQ TS remains active. An independent LM393LV window drives CE through a fail-off transistor path. 5.23 kΩ to REGN and 30.9 kΩ to ground bias the NTC. The comparator threshold pairs are 52.3 kΩ/100 kΩ cold and 107 kΩ/100 kΩ hot, with 10 MΩ positive feedback. The calculation includes ±3% NTC resistance, ±0.1% threshold resistors, comparator offset, REGN range and output state. Charge starts/stops within approximately 13.70–16.23 °C at the cold boundary and 39.01–41.23 °C at the hot boundary. Open/short thermistor faults inhibit charging. These conservative thresholds preserve margin for the pack's 10–45 °C limits; attachment delay and surface gradients require a pack-level thermal test.

BAT_READY uses TLV3012B with 158 kΩ, 100 kΩ and 2.15 MΩ hysteresis. Its rising bounds are 3.213–3.374 V and falling bounds 2.956–3.127 V. It authorizes MCU/USB recovery, while capture requires battery ≥3.55 V or a suitable Type-C source. Firmware warns at 3.4 V and stops acquisition at 3.2 V measured on `VBAT` after the fuse and connector path. This capture cutoff is a host/firmware measurement point, separate from the protected pack output and its internal PCM thresholds. The switched 100 kΩ/100 kΩ battery divider requires 50 ms settling and calibrated ESP32 ADC readings.

The one PTS636 button directly drives RTC-capable GPIO2. Firmware validates an 800 ms turn-on hold, enters pairing on a continuous 3 s hold, and shuts down acquisition after a 1.5 s hold while running, then sleeps after release. The common-anode Kingbright RGB indicator uses three active-low expander outputs. `firmware-contract.json` records all GPIO and expander assignments. IO0 P17 is SD_EN, with its switch/default resistor owned by the SD interface. The hand IMU is polled; unused IO1 P07 has a 10 kΩ pulldown.

## Verification and assembly

`power_checks.py` writes tolerance calculations and explicit qualification limits to `power-check-results.json`. `generate_native.py`, KiCad XML export and `reconcile_native.py` independently check every native schematic pin against the source, including intentional NC pins. `validate_footprints.py` loads every used land pattern in KiCad 7 and checks its physical pad-number set. Native symbols expose exact manufacturer pin numbers; the pin reconciliation does not substitute for a functional electrical review.

`footprint-sources.json` records content hashes and manufacturer/pinned-library provenance. The TPS22950 uses its exact 6-ball YBH WCSP land: 0.20 mm copper, 0.40 mm pitch, 0.04 mm mask expansion, 0.21 mm paste aperture. Its recommended 75 µm stencil region needs assembler review alongside the 100 µm diode stencil recommendation. The BQ25616 exposed pad uses segmented paste and needs an engineered thermal-via pattern. The TPS63070 RNM power pads and solder-mask-defined regions need the manufacturer's drawing carried through the board fabrication review. These assembly details are part of the full-board manufacturing gate.

`run_buck_sweep.py` runs bounded ngspice42 analyses of the unmodified TI TPS63070 PSpice macro. The runner loads XSPICE code models and enables PSpice compatibility; it records native completion before interpolation and retains each execution attempt. A zero process exit alone is insufficient. The finite-impedance attempt status is recorded in [battery-path-transient-review.md](battery-path-transient-review.md). `simulation/buck-results.json` distinguishes nominal model results, corner results, timeout/error attempts and physical qualification. The previous constant-current startup load artificially pulled the unpowered output negative and was replaced by a resistive initial load. Startup results use PWM, matching the hardware default.

The current V4 energy record uses the 6.5 Ah minimum pack at 3.6 V: 23.4 Wh nominal and 18.72 Wh after the explicit 20% capacity reserve. Its conservative sustained design case calculates 6.019271 h after reserve, with a 0.019271 h margin over six hours; the realistic duty case calculates 7.671136 h. The instantaneous peak-converter sizing case is 4.52682 h and is not a sustained-runtime prediction. These are engineering calculations pending measured camera, radio, SD, sensor, path-loss and thermal acceptance. See [energy-budget.json](../verification/energy-budget.json).

Recovery from a depleted pack on a default USB source requires physical qualification: the BQ25616 poor-source test is 30 mA typical with no guaranteed maximum, while the recovery limiter guarantees 34 mA minimum under its stated conditions. The charger/limiter DPM interaction, cable inrush, MCU enumeration and time to BAT_READY must be measured together. Both limiters reverse-block; the TPS2553 reverse-detection delay and the charger's battery-input blocking require a detach/backfeed test. Low-current recovery can reach the charger's timer before a full large-pack charge, so full-charge qualification uses a Type-C source advertising at least 1.5 A.

The complete board must also verify effective MLCC capacitance under bias (60 µF main model, conservatively retained 24 µF analog shutdown bound), regulator startup/step response, analog/reference shutdown, charger/cell temperature, USB enumeration/suspend and all camera/SD load combinations. Calculation and vendor-model passes establish the stated modeled behavior; physical performance remains a prototype verification task.

## Reproduction

```sh
python3 build_power.py
python3 power_checks.py
python3 generate_native.py
kicad-cli sch export netlist --format kicadxml -o native.xml glove-v4-power.kicad_sch
python3 reconcile_native.py native.xml
kicad-cli sch export pdf -o native.pdf glove-v4-power.kicad_sch
python3 validate_footprints.py  # Python environment with pcbnew
python3 run_buck_sweep.py --ngspice /path/to/ngspice --cm-dir /path/to/ngspice/code-models
```

Primary sources are cited per component in the circuit. The battery source is <https://www.jauch.com/downloadfile/61f0fb7230945444b292c0fac704609f8/6700%20mAh,%20LI18650JLS%20HB%201s2p,%20Mat.%20250480.pdf>; the unmodified TI regulator macro is <https://www.ti.com/lit/zip/slvmbp8>. The cached Nexperia diode drawing is the manufacturer's July 2023 PDF obtained from a distributor mirror after the manufacturer CDN rejected direct download; its identity and drawing were inspected visually.

Murata SimSurfing DC-bias data exposed insufficient margin in the original 22 µF 0805 choice. Nine reservoirs now use GRM32ER61C476KE15L, 47 µF 16 V ±10% X5R 1210, 2.7 mm maximum height. At 3.6 V, the three-part bank gives 74.44 µF after the worst available −20/25/85 °C typical curve, 10% tolerance and a further 20% allowance. The corrected 60 µF model reaches 3.31192–3.49303 V at the 1 A step. The earlier 100/60 mV transient allocation failed; the documented PWM-specific 120/100 mV allocation retains datasheet rail margin. These results do not characterize production variation or PCB parasitics. Run `python3 analyze_buck.py` to reproduce the saved-waveform analysis.

The selected battery is Jauch 250480, factory PCM and fuse, minimum 6.5 Ah at 3.6 V, 69 × 38 × 20 mm, 100 g, maximum 2 A charge and 10–45 °C charge window. The separate 103AT-2 remains required. Current runtime calculations are in [energy-budget.json](../verification/energy-budget.json); physical runtime and thermal performance remain acceptance measurements.
