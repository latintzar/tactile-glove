# v3 electrical adversarial review — 2026-10-22

Status: candidate review only. This file audits the current manifest and existing one-cell simulations. It does not change the canonical electrical files or make the board order-ready.

## Release blockers

### 1. The charge amplifier clips at the documented stress charge

The current cell uses 100 MΩ || 100 pF, biased at 1.25 V. The ideal feedback charge range is approximately `Cf × 1.25 V = ±125 pC` before reaching either ADC rail. The existing simulation report records a 250 pC stress event reaching `-1.437 V` in the linear model, and the vendor-model stress run drives the amplifier/filter chain to approximately 0.001 V or 3.299 V. The current 1 kΩ PVDF series resistor limits fault current but does not prevent the op-amp input/output from saturating.

Minimum fix: define the maximum expected charge from the actual PVDF laminate and mechanical impact, then choose one of: larger `Cf`, lower input gain, or a verified low-leakage clamp/limiter around the charge amplifier. The clamp leakage must be budgeted against the 100 MΩ feedback path. Add a transient test with the chosen protection, the PVDF capacitance, cable capacitance, and the MCP6004 model. Until that test exists, the dynamic range and recovery claim are not releasable.

Evidence: `hardware/glove-v3/simulation/report.md` (stress, headroom, and vendor-model sections); `hardware/glove-v3/electrical/components.json` (`RFB_*`, `CFB_*`, `RIN_*`).

### 2. The 20-channel mux settling claim is only arithmetic

Firmware allocates 2 µs dynamic settling and 8 µs pressure settling after changing the 4067 bank/final mux controls. The simulation report explicitly omits mux parasitics, routed wiring, charge injection, and the 20-channel board. The local `cd74hc4052.pdf` is a 4052 datasheet, not the manifest’s `CD74HC4067M`; the exact 4067 electrical limits and switch capacitance are therefore not locally evidenced. The current 2 µs number cannot establish settling to 16-bit ADC accuracy after a channel change.

Minimum fix: add the exact TI CD74HC4067 datasheet to `electrical/sources`, then simulate or measure the worst-case path: sensor/filter output impedance, 4067 on resistance and capacitance, OPA4320 follower, final 4052, OPA320 driver, 22 Ω isolation resistor, and 1 nF ADC bucket. Use a settling criterion tied to the 16-bit target (approximately 0.5 LSB at the selected full-scale span), and measure all bank/output combinations. If the result does not fit the 50 µs dynamic slot, increase the settling interval or reduce the scan rate.

Evidence: `firmware/tactile_v3/tactile_v3.ino` (`DYNAMIC_SETTLE_US=2`, `PRESSURE_SETTLE_US=8`); `hardware/glove-v3/simulation/report.md` (explicit omission of mux and routed parasitics); `hardware/glove-v3/electrical/sources/cd74hc4052.pdf` (wrong mux family for closing the 4067 claim).

### 3. ADC driver timing is a bound, not a validated path

The MCP33131D-10 requires 1.8 V AVDD, DVIO 1.7–5.5 V, VREF 2.5–5.1 V, and supports up to 100 MHz SCLK. The firmware uses 16 MHz SPI, 1 µs CNV high, 1 µs conversion wait, and a 2-byte transfer. The existing report estimates roughly 1.02 µs as a conservative acquisition allowance after adding the OPA320 and ADC input network, but it does not simulate the switched ADC input or the mux chain. The report therefore supports timing arithmetic only; it does not demonstrate 16-bit settling.

Minimum fix: run a switched-capacitor transient with the exact MCP33131 input model or bench-test the OPA320/22 Ω/1 nF network at the selected CNV and SCLK timing. Capture worst-case first-sample error after every mux transition. Keep the current 16 MHz schedule only after the measured error meets the stated resolution target.

Evidence: `hardware/glove-v3/electrical/sources/mcp33131.pdf`, pp. 1, 4–5 and the input electrical table; `hardware/glove-v3/simulation/report.md`, “MCP33131 acquisition budget.”

### 4. Reference and midpoint stability are not closed

The MCP1501 SOIC-8 pin map is VDD pin 1, SHDN pin 3, OUT pin 7, FEEDBACK pin 8, and ground pins 2/4/5/6. The manifest connects pin 3 high and ties OUT/FEEDBACK, which is the intended topology, but the 2.5 V output has only the manifest’s 10 µF VREF capacitor and no documented startup/settling test under ADC load. The datasheet recommends a local 0.1 µF capacitor at VDD. The MCP33131 input range and calibration are reference-sensitive.

The VMID divider is 10 kΩ/10 kΩ with 1 µF bypass and an MCP6002 follower. Its nominal Thevenin resistance is 5 kΩ, so the nominal midpoint is reasonable, but the design has no tolerance, startup, load-step, or reference-noise result. Every charge amplifier and mux unused-channel bias node uses VMID; any midpoint disturbance is common to the whole analog chain.

Minimum fix: document the MCP1501 VDD bypass placement/value, reference startup to valid ADC sampling, and VMID tolerance/load-step/noise limits. Simulate or measure VMID with all 20 charge amplifiers, 40 filter stages, mux bias connections, and ADC AIN− connected. Recalibrate the ADC after reference startup as required by the MCP33131 data sheet.

Evidence: `hardware/glove-v3/electrical/sources/mcp1501.pdf`, pp. 1, 3 and sections 1.1–1.4; `hardware/glove-v3/electrical/sources/mcp33131.pdf`, pp. 1 and 4–5; `components.json` (`R_VMID_H`, `R_VMID_L`, `C_VMID`, `C_ADC_REF`).

### 5. The analog supply map needs a physical power integrity review

The TLV75518 DBV pin map is IN 1, GND 2, EN 3, NC 4, OUT 5. The manifest’s nets put 3V3 on pins 1 and 3, NC on pin 4, and 1V8 on pin 5, which is electrically consistent with EN tied high. The local TI datasheet requires at least 1 µF input and output capacitors; those parts exist in the manifest. The remaining blocker is placement and load-step evidence: the ADC AVDD, its reference input behavior, and the OPA320/ADC driver are not validated against the LDO transient response or 1.8 V rail noise.

Minimum fix: perform a rail-load transient using the MCP33131 conversion current, OPA320 output activity, decoupling ESR/derating, and the actual 1.8 V plane/return path. Keep the 1.8 V ADC AVDD separate from noisy digital return paths in layout review.

Evidence: `hardware/glove-v3/electrical/sources/tlv755p.pdf`, pp. 2–3 and pin table; `components.json` (`C_LDO_IN`, `C_LDO_OUT`, `C_ADC_AVDD`).

### 6. XIAO charger and battery behavior is not proven by this circuit audit

The manifest identifies the XIAO module as `102010469` with onboard charging and connects BAT+/GND to the battery connector. The firmware reads a battery divider and displays a percentage-like millivolt value, but the circuit evidence here does not prove the selected protected battery connector polarity, charge-current configuration, thermal behavior, or USB/battery power-path behavior of the exact XIAO Sense revision.

Minimum fix: attach the exact Seeed schematic for `102010469` to the electrical evidence set and verify BAT+, charger current, USB VBUS isolation, battery protection assumptions, and the connector pin orientation against the selected Adafruit 1578 lead. Treat the displayed battery value as voltage until a chemistry-aware calibration is documented.

Evidence: `hardware/glove-v3/electrical/components.json` (`J_XIAO`, `J_BAT`); battery evidence is separately recorded under `component-evidence/battery`.

## What the current simulations establish

The current simulations establish one representative PVDF charge amplifier plus two nominal Sallen-Key stages. They include cable-capacitance sweeps and a vendor-derived MCP6001-family macro-model run. They do not include the exact MCP6004 package/model in the complete 20-cell circuit, mux charge injection or capacitance, OPA4320 bank buffers, OPA320/MCP33131 switched-input behavior, routed PCB parasitics, sensor mechanics, noise, or measured PVDF sensitivity. The net validator proves graph endpoint coverage, not analog correctness.

The report’s 4 kS/s/channel arithmetic is internally consistent as a coarse schedule: 20 dynamic channels in 250 µs and one pressure channel per frame every fourth frame. It remains a timing budget rather than a demonstrated interrupt execution result; the firmware itself marks complete ISR timing as bench-gated.

## Minimum gate before ordering

Close the charge-overload test, exact-4067 settling test, ADC switched-input settling test, reference/VMID load and startup test, and XIAO charger/power-path verification. Then rerun the 20-channel timing and analog tests with routed parasitics before treating the board as order-ready.
