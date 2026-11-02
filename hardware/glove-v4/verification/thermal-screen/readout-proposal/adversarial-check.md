# Bounded readout audit

**The arithmetic is consistent after corrections. A protective temperature guarantee remains unqualified.** This audit changes only the isolated proposal.

| Check | Result |
|---|---|
| Primary nominalR-T data and inverse conversion | PASS:19 table endpoints,161 integer-temperature roundtrips and independent35°C geometric-mean interpolation |
| Ratiometric formula | PASS with actualr and2.45/2.55V excitation; the previous fixed2.5V scaling in the error calculation is corrected |
| Independent errors | PASS after adding separate signal-level±1mV/read error, sensor-return±5mV displacement and0–1Ω wire/contact resistance. Sensor-buffer/VMID offset extrema remain independent; common linear offset cancellation is separate |
| Self-heating | Added0–0.15°C to the sensor temperature before resistance conversion. This is an installed acceptance allocation; the manufacturer's typical dissipation factor alone is not its guaranteed bound |
| Open/short detection | PASS under declared allocations: openq≥0.9822 versus0.94 limit; shortq≤0.0508 versus0.06 limit |
| Protective36°C cutoff | FAIL as a guarantee:36+3+1=40°C consumes all reserve, before unqualified terms |
| Power-down behavior | UNRESOLVED: retained filter/reservoir charge can inject into collapsing rails; the prior steady-state explanation did not establish transient input limits |

The revised2048-corner sweep gives indicated37.419–43.009°C at true40°C, or−2.581/+3.009°C. The2kΩ stress expands this to−3.945/+4.766°C. These are sensitivity bounds **conditional on** the declared acceptance allocations. MCP6002 offset/bias and selected3.3V mux resistance/leakage require qualification; the extra ground/analog-error/self-heating allocations also need evidence.

The conversion uses the nominal manufacturerR-T table with log interpolation. R25/B tolerance perturbations and the0.25°C interpolation allowance do not establish a manufacturer-guaranteed full-curve envelope. PCB/sensor temperature need not match; the sweep separately permits0–85°C board drift. Long-term thermistor ageing/strain and circuit drift are not closed by initial calibration.

A release threshold must satisfy:

`Ttrip + worst accepted under-reading + sensor/contact gradient + detection/shutdown temperature rise + post-shutdown overshoot + positive reserve ≤40°C`.

Within-cohort VEXC/VMID movement, sensor-filter dynamics, local/hottest-cell gradients, thermal response lag, sample age, shutdown latency, stored heat after shutdown, and continued USB standby dissipation need measured bounds. A plausible stuck reading/detached sensor also remains outside universal fault coverage. The36°C and45°C settings are provisional test settings. Raising base cutoff to37°C after a2°C calibration bound also leaves zero reserve under the old1°C lag allocation; it is not an automatic release rule.

The SHA256 manifest is regenerated after all final proposal edits. It covers every regular file in this folder recursively except the manifest itself; source PDFs outside the folder retain their separate hashes in`sources.json`. No large simulation, rendering or canonical regeneration was performed.
