# V4 analog and acquisition simulation coverage audit

**Date:** 2026-10-23
**Scope:** read-only comparison of the current V4 tactile manifest and requirements with saved V3/V3.3 analog and acquisition evidence.

## Verdict

Coverage is partial. The V4 tactile component/value topology is carried forward from the V3.3 manifest, so the prior PVDF and mux decks are useful incremental evidence. They are not V4 assembled-board validation and do not cover the V4 rail network, full differential ADC path, sensor ranges, shared-channel crosstalk, or a 20-channel analog schedule.

The V4 feedback descriptions are now corrected in [components.json](../electrical/components.json): the actual feedback MPN/value fields are **22 MΩ** and **470 pF** (`RV0805FR-0722ML`, `GRM1885C1H471JA01D`), matching the saved decks. The inherited V3 result remains provenance; a V4-named netlist rerun is still needed.

## What is covered

- [V3.3 signal-chain results](../../glove-v3/verification/signal-chain/results.json) checks the 20-site passive topology against the manifest and runs one-cell SPICE cases with 531 pF PVDF, 50/150/300/1000 pF cable values, 100 kΩ input, BAV199 clamps, 22 MΩ/470 pF feedback and two filter stages.
- The same suite includes 20–2000 Hz charge excitation, ±250/±500 pC, ±50 nC protected overload cases, and a 3,000-draw passive tolerance sweep. Two native negative cases (`canonical--1pC`, `canonical--250pC`) are incomplete; numerical 1 fF shunt reruns are separately labeled regularization.
- [Mux/ADC results](../../glove-v3/verification/mux-adc/results.json) has seven complete proxy cases. It exercises OPA4323/OPA320 models, 1 kΩ and 2 kΩ assumed mux resistance, 80/40 pF and doubled capacitance, 10 kΩ pressure source, and 22 Ω + 1 nF + 200 Ω/31 pF ADC loading. It does not model the physical switch or switched SAR.
- [Power and bias validation](../../glove-v3/verification/power-simulation.md) covers the inherited REF3330 load/headroom arithmetic, VEXC dual-loop 47 Ω/10 kΩ/100 nF cases with 0.8/1/1.2/2 µF bulk and a 5 mA step, plus VMID driving all 20 passive filter branches at 0.1/1/10 nF direct parasitic cases. V4 retains those VEXC/VMID values, including the 1 µF VEXC reservoir.
- The native firmware fixture proves synthetic data framing and one-channel 4 kS/s handling. It does not prove analog acquisition or material response.

## Missing or stale coverage

1. **V4 rails and excitation:** inherited V3.3 power validation already covers REF3330 load/headroom arithmetic, the VEXC dual-loop with 0.8/1/1.2/2 µF bulk cases and a 5 mA load step, and VMID driving all 20 passive filter branches with 0.1/1/10 nF direct-parasitic cases. The remaining gap is coupling those proven blocks to the V4 3.416 V rail, rail gates, startup/shutdown, decoupling impedance and ADC/reference load.
2. **Differential ADC path:** existing mux decks drive a single-ended 0.1–2.5 V source. They omit V4’s negative OPA320 path, differential common-mode, reference kickback, CNV/SCK switched behavior and the 1.8 V ADC supply.
3. **Pressure behavior:** the proxy uses a 10 kΩ source and 0–2.5 V endpoints. There is no measured Velostat/Linqstat resistance range, nonlinear/hysteretic model, pressure/PVDF simultaneous case, 20-channel crosstalk case, or 50 Hz analog schedule.
4. **PVDF overload:** negative native overload cases remain solver-incomplete. No V4 rail-clipping, recovery, physical PVDF overstress, noise, force-to-charge or temperature evidence exists.
5. **Cable/mux crosstalk:** single-channel cable capacitance and doubled proxy capacitance are covered. Routed harness extraction, shared returns, switch charge injection and consecutive-channel crosstalk are absent.
6. **Digital controls:** camera translator static margins are checked, while tactile mux-address latch, CD74HC4067 controls and ADC CNV/SCK/SDO voltage/timing are not simulated. The camera check itself leaves dynamic waveforms for target integration.
7. **Sampling schedule:** firmware evidence reports the target schedule, but no analog simulation drives 20 PVDF channels at 4 kS/s/channel plus 20 pressure channels at 50 Hz/channel under common reference and mux loading.

The machine-readable matrix, hashes and follow-up requirements are in [analog-coverage-2026-10-23.json](analog-coverage-2026-10-23.json). The concrete next coupled case is a 3.416 V transient containing the REF3330 reservoir, VEXC 1 µF plus 20×10 kΩ pressure load, all 20 VMID filter branches, one mux transition, one PVDF pulse and one pressure step during the 250 µs scan; record rail ripple, VEXC/VMID settling, differential ADC settling and selected-channel crosstalk.

## Subsequent execution in this review

The [differential ADC campaign](differential-adc/README.md) now includes both input drivers and identifies the pressure12 µs settling defect, corrected to24 µs. Five native cases complete and satisfy the selected settling bounds. The [coupled20-channel campaign](coupled-analog/README.md) attempts all active bias/charge/filter circuits; the original seven attempts remain incomplete, while one later conditioned native trace completes with failed tolerance-sensitivity checks and remains diagnostic. The [thermal screen](thermal-screen/README.md) records the current case heat-path and battery-mode sensing limitations. These newer results refine the gaps listed above; they do not extend single-cell evidence into a whole-board pass.
