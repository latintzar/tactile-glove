# Pack and contact temperature readout proposal

**Primary correction: two independent103AT-2 thermistors, a dualMCP6002 buffer, and two spare pressure-bank channels.** This folder is an unapplied engineering proposal. [proposal.json](proposal.json) contains the exact netlist/BOM delta: nine new main-board components, two resistor replacements, and three U6 net changes. The canonical561-part circuit, enclosure and firmware remain unchanged by this proposal.

## Existing control path

The charge thermistor connects J13/J_NTC pin1→BAT_TS and pin2→GND. BAT_TS reaches BQ25616/U42 pin11 and LM393LV/U43 pins2/5. U43 outputs1/7 form NTC_VALID, which drives Q3 to control U42 pin9/CHG_CE_N. NTC_VALID has **no MCU or expander input**. U43, its thresholds and the TS pullup run from CHG_REGN; the BQ25616 turns REGN off in battery-only operation. Reading this comparator would therefore not provide recording-temperature protection.

U52/TCA9535 pin19=P16=globalbit14 drives CHG_DISABLE through Q4. U53 pin6=P02 exposes generic CHG_STAT_N; pin7=P03 exposes USB_PG_N. The existing `firmware/tactile_v4/main/app.cpp` power task reads battery voltage and USB qualification. A thermal fault must reach the full stop path, including camera power, storage and charging. Merely clearing acquisition enable leaves the camera task running in the inspected implementation. Root is correcting the broader power-fault latch separately.

## Proposed circuit

| Function | Exact connection |
|---|---|
| Pack NTC | J17 pin1 TEMP_PACK_RAW; pin2 GND; independent103AT-2 |
| Base NTC | J17 pin3 TEMP_BASE_RAW; pin4 GND; independent103AT-2 |
| Pullups | R250/R251 RT0603BRD0710KL,10kΩ0.1%25ppm/°C, VEXC2V5→respective RAW node |
| Node filters | C206/C207 GRM188R71H104KA93D,100nF, RAW→GND |
| Pack buffer | U54 MCP6002T-I/SN: pin3=RAW, pins1/2=TEMP_PACK_BUF |
| Base buffer | U54 pin5=RAW, pins6/7=TEMP_BASE_BUF |
| Buffer supply | U54 pin8=3V3_A, pin4=GND; C208100nF between pins8/4 |
| Output isolation | R252/R253 RC0603FR-07100RL100Ω, BUF→TEMP_PACK/TEMP_BASE; feedback stays before each resistor |
| Pack mux | U6/CD74HC4067 pin21/I10, bank0 slot10: VMID1V25→TEMP_PACK |
| Base mux | U6 pin20/I11, bank0 slot11: VMID1V25→TEMP_BASE |
| Midpoint reference | U6 pin19/I12, bank0 slot12 remains VMID1V25 |
| Excitation reference | U6 pin18/I13, bank0 slot13: VMID1V25→VEXC2V5 |
| Midpoint accuracy | Replace R141/R142 with RT0603BRD0710KL; values/nets/footprints stay10kΩ |

The existing charge NTC and its comparator remain electrically independent. There are three physical thermistors after integration. The buffer prevents mux leakage flowing through the thermistor's several-kΩ Thevenin resistance. The100Ω resistor isolates the op-amp from mux capacitance; the100nF filter belongs at the continuously powered sensor input, not the multiplexed output.

J17 reuses the exact existing `GloveV4:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal` footprint. Candidate front placement is(15,43.5),90°, mouth toward−X; courtyard[11.72,39.60,18.28,47.40]. The PCB owner verified courtyard clearance. [local-fit.json](local-fit.json) independently checks its complete approach envelope against561 component solids and42 manufactured solids. U54 candidate front placement(27.25,52),0° is reserved by the PCB owner; all eight proposed IC/passive courtyard prisms also clear current components/manufactured solids in [board-proposal-fit.json](board-proposal-fit.json). Exact proposed coordinates are retained in [placement-proposal.json](placement-proposal.json); the pack output-isolation resistor is9mm from its buffer and should move closer during routing. Complete cable routes await coordinated integration.

## Harness and sensor attachment

Use one SHR-04V-S housing, four SSH-003T-P0.2-H contacts, and four28AWG stranded wires with0.4–0.8mm insulationOD, matching the [JST primary contact specification](https://www.jst.com/wp-content/uploads/2025/06/eSH.pdf). Mark housing and PCB `TEMP`; its polarization is mechanical, while differentiation from the other4-pinSH connector is an assembly-label requirement.

103AT-2 has solid square leads: join them to flexible wires at the factory, insulate each joint, and strain-relieve the flexible cable separately. Follow [Semitec](https://www.semitec-global.com/uploads/2022/01/P12-13-AT-Thermistor.pdf): bend≥3mm from the head; solder≥5mm from the head,≤7s at340°C. Its solid leads do not enter the SH crimp. Verify finished resistance and isolation after assembly.

Local reserved sensor envelopes pass actual solid checks: pack sensor X36..44,Y21..25,Z24..26, beside the independent charge sensor; base sensor X24..32,Y64..68,Z1.3..3.3, on the inner wrist-facing floor. These are maximum bonded-envelope reservations, not a claim that the two-cylinder pack itself has a flat top. Bond the pack head to the actual cell wrap without loading leads; bond the base head against the floor. Final adhesive thickness, strain relief, complete wire bends/lengths and gradients need the coordinated mechanical integration. The left-edge service route must remain separate from the battery power-harness corridor and clamping faces.

## Conversion, accuracy and faults

For signed ADC readings `Ds`(sensor), `Dm`(VMID), `De`(VEXC), and actual `r=VMID/VEXC`:

```
x = (Ds - Dm) / (De - Dm)
q = r + (1-r)*x
Rntc = Rpull*q/(1-q)
T = inverse_log_interpolation(Semitec_R_T_table, Rntc)
```

Use `r=0.5` only with the error budget. A factory measurement of actualVMID/VEXC can remove initial divider/buffer offset, while temperature drift remains bounded separately. Ground is **not** a calibration endpoint: the measured/modelled OPA path clips near21.39mV. Common linear ADC/path gain and offset cancel in the differences; switch-channel-dependent leakage, amplifier nonlinearity and drift do not.

[calculate.py](calculate.py) preserves the primary nominalR-T table and separately accounts for R25±1%, B25/85±1%, precision-resistor tolerance/drift,±7mV qualified buffer-offset allocations,±2nA buffer-input-current allocation, ADC±8counts per reading, and a0.25°C interpolation acceptance allocation. The adversarial correction additionally includes0–0.15°C self-heating,0–1Ω sensor wiring/contact resistance,±5mV sensor-return ground displacement and±1mV independent signal-level path error per reading. ADC scaling now uses each actualVEXC corner and a3.03V reference ceiling. These added limits are explicit qualification allocations; the self-heating limit requires measurement because the published dissipation factor is typical. The buffer offset/current allocations exceed typical datasheet curves; they are explicit electrical acceptance requirements, not new manufacturer guarantees. TI specifies off-switch leakage±8µA at6V and gives Ron limits at4.5/6V, rather than a guaranteed selected-path sum at3.3V.

With a qualified≤500Ω selected-mux resistance and≤8µA effective leakage per sampled channel, including independent reference-channel drops, the uncalibrated calculated bound at40°C is−2.58/+3.01°C. The deliberately severe2kΩ case expands this to−3.95/+4.77°C. Buffering improves the rejected unbuffered scheme; it does not make the existing mux's undocumented3.3V maxima disappear. Qualify the total assembled temperature transfer over the relevant mux patterns and0–85°C board conditions. The proposed≤3°C symmetric error acceptance is not fully established by this allocation sweep: its positive error is3.01°C at40°C. A36°C cutoff plus3°C accepted error plus1°C gradient/lag reaches40°C with zero additional reserve. A37°C cutoff with2°C accepted error has the same zero-reserve issue. Neither is a protective guarantee; release requires a measured one-sided under-reading bound, all thermal/control overshoot and a positive allocated margin. This is calibration of the complete sensing path, not an assumption that unknown leakage cancels.

Before converting temperature, reject: nonfinite/overflow data, reference span outside12800..14500counts, |Dm|>200counts, q<0.06(short), q>0.94(open), R outside the retainedR-T table, or a cohort older than500ms. Faults trigger stop immediately and never become clipped “safe” temperatures. Updated open/short corners include the added signal-level error and ground offset and retain separation(qopen≥0.9822,qshort≤0.0508); native open produces≈2.533V atAIN+, and short≈21.39mV. The selected45°C pack and36°C base thresholds lie in the linear midrange. A stuck plausible reading, detached sensor, identical wiring swap, or unmodelled leakage remains a diagnosable/testable fault class rather than a universal single-fault guarantee.

After VEXC/3V3_A and the node capacitors discharge, both passive NTCs pull their nodes toward ground; there is no external sensor supply to sustain back-power, and samples are invalid. During power-down, the100nF node capacitors and VEXC reservoir retain charge: input/rail injection and differential-input limits must be checked against the MCP6002±2mA input-current absolute maximum. The current steady-state argument does not validate that transition. Measure only after rails stabilize. Maximum node time constant is≈1.29ms including capacitor tolerance; wait≥20ms after rail-ready before the first valid cohort. Existing startup settling is longer.

## Supply and native model checks

The conservative retained load budget is5.803mA: twenty shorted pressure pullups, two shorted thermal pullups, the midpoint divider and8µA reference loading at2.55V. It deliberately keeps the older1% pullup minima, so the precision replacements improve margin. Two normal25°C sensors add0.25mA; their simultaneous-short allowance is0.515mA. U54 draws from3V3_A, separately from VEXC; reserve its datasheet supply current for both amplifiers in the revised power budget. Thermistor self-heating is at most0.164mW, approximately0.082°C using the manufacturer's typical2mW/°C dissipation factor.

Original MCP6002 dual-feedback VEXC model runs at5.81mA complete at both3.3V/2.5V and3.111665V/2.55V. The lower-supply case settles to2.549224V, recovering to0.1% in4.56ms. The47Ω+1% isolation drop leaves≈0.286V raw-output headroom. [vexc-results.json](vexc-results.json) records actual simulator27°C; the original model represents typical room-temperature behavior and explicitly excludes production/temperature/specification variation with supply. It does not guarantee hot output current.

The complete proposed sensor-buffer/analog-chain native runs in [buffer-results.json](buffer-results.json) use3.111665V, original MCP6002/OPA4323/twoOPA320 models,2kΩ/160pF and2kΩ/80pF mux stresses,±8µA leakage and the actual22Ω/1nF ADC buckets with31pF/200Ω acquisition equivalents. All four80µs runs complete; the worst24µs settling residual is0.232µV and last half-LSB crossing5.77µs. DC leakage error≈±17mV is reported separately. Initial Gear runs failed at the initial timepoint; their logs are retained. The successful trapezoidal runs pass native endpoint/finite-data/error checks. Switching charge injection, physical wiring and hot/cold silicon remain physical acceptance work.

## Firmware interface

Read slots10,11,12,13 from the existing bank0 ADC path as one cohort every100ms. Use24µs acquisition wait per slot. Schedule one extra read on four otherwise unused non-pressure ticks within2ms; keep SPI/mux ownership in the acquisition ISR and perform conversion/filtering in the task. The present250µs budget has64µs arithmetic margin; one extra24µs read plus conversion/clock overhead fits that arithmetic, with actual ISR timing to be measured. Do not insert all four extra reads in one frame.

Boot with CHG_DISABLE asserted. Enable sensor rails at low load, wait for valid references and two valid thermal cohorts, then allow capture. Initial trip thresholds: pack≥45°C or base≥36°C for two consecutive cohorts. Either invalid sensor/reference/cohort stops after one cohort. These remain provisional test thresholds. For wear, require Ttrip + worst accepted under-reading + sensor/contact gradient + detection/shutdown delay temperature rise + post-shutdown overshoot + positive reserve ≤40°C. The former36+3+1 allocation leaves no reserve and does not close that condition. Cohort reference motion/filter lag, thermistor ageing/strain and long-term circuit drift, local hot spots, retained heat after shutdown and USB standby heating are additional unqualified terms; the present calculation does not bound them. At35°C ambient this conservative setting may prevent continuous operation. Availability is explicitly subordinate to the measured thermal operating envelope.

The stop handler latches the thermal reason, immediately disables charging and requests cameraPWDN/reset, then stops recording/ADC/storage and powers down camera rails. A single explicit atomic stop path must govern both camera and acquisition. Preserve CHG_DISABLE across sleep or reassert it at every boot before optional charge enable. Restart requires a button wake and valid pack≤40°C/base≤33°C readings; a sleeping unpowered ADC cannot infer cooling. The independent charge-window circuit remains responsible for charge cold/hot limits even if firmware is absent. Firmware safety control does not establish a fail-safe guarantee for a stalled MCU/expander bus.

## Outward heat path

The sustained-contact target applies to the wrist-facing base/textile. A briefly touched outer lid may use a separately qualified material/contact-duration limit. The earlier40°C limit on every exposed surface was an intentionally restrictive comparison, not a universal outer-lid requirement. At35°C ambient, an isothermal50°C top/sides could reject3.81–6.75W in the sampled natural-convection/radiation range; local nylon temperatures still depend on actual spreading.

**Thermal-path design target:** add an electrically insulated electronics→outward-shell path with effectiveR≤5K/W(≥0.2W/K), while preserving RF/camera/button/connector clearances and adding no conductive shortcut toward the wrist floor or cell wrap. Target the MCU/regulator heat at the PCB/shield region, spread it over≥4000mm² of outward lid/sides, and mechanically support contact pressure from the enclosure rather than small component packages. A thin internal metal plate alone leaves the13.6mm air gap intact and therefore does not meet this requirement.

A practical next mechanical concept is a supported formed aluminum bridge plus broad lid spreader and compliant electrically insulating contact pads. Budget≤2K/W for bridge/pads/spreading and≤3K/W through adhesive/nylon to air-facing surface. At kPA12=0.127W/(m·K), the existing1.3mm roof over4000mm² alone is2.56K/W; local ribs and patchy bonding increase it. This establishes real area/contact requirements for CAD and supplier review. Conductivity, pad compressive load, source-side contact area and safeRF spacing must be specified before that part becomes a fabrication item; this folder does not claim an unmodelled bridge fits.

[outward-path-results.json](outward-path-results.json) adds exactly that conductance to the existing five-node screening model. At25°C ambient/defined34°C-R15phantom, sustained base falls41.3–50.0→36.2–40.8°C, pack42.0–57.4→36.6–45.0°C. At35°C, the improved base remains40.2–45.2°C; at40°C it is42.0–47.6°C. These sensitivities support outward heat extraction and independent thermal shutdown. They do not authorize35–40°C continuous wear or replace the instrumented six-hour test in the parent report.

The dimensioned [roof-insert/MCU-bridge candidate](heatpath-candidate.md) separates a local shield-to-metal thermal target from the whole-case sensitivity. Its [drawing](heatpath-candidate.svg) and Boolean envelope checks preserve the current external dimensions and explicitly identify the replaced lid material. It adds approximately18.5g net before its gasket/pad/fasteners. Pad-force and roof-capture detailing remain before fabrication.

## Integration and reproduction

Integrate only after coordinated source/routing review: update canonical source/endpoints/BOM and energy load, place the nine new parts, route U6/reference connections, then model the complete sensor harness/attachment and rerun clearance. The isolated [C++ temperature policy](firmware/README.md) now passes its native sanitizer and fault tests. Integrate its acquisition/cohort and shared-stop consumers before enabling temperature-qualified capture. Preserve the independent charge NTC.

Run `python3 calculate.py`, `python3 outward_path.py`, and `PYTHONPATH=/tmp/glove-engineering/auditdeps python3 run_buffer.py` from this folder or by absolute path. `run_vexc.py` writes its native evidence to `/tmp/thermal-readout-proposal`. [sources.json](sources.json) binds primary documents to local hashes. [The bounded adversarial check](adversarial-check.md) records the arithmetic passes and qualification failures. This proposal is ready for electrical/firmware review; it is not an implemented thermal-safety or wearability release.
