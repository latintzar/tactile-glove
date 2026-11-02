# Right-hand tactile glove —V3.3 core

Current completed electrical baseline:20 separately read pressure locations and20 PVDF vibration locations, one button and a diffused RGB indicator. The next complete-product requirement adds continuous finger-facing video for at least six hours, with twelve hours as the stretch target. Its camera, controller and larger-battery power design remain under integration review.

## Files

- `electrical/components.json`:356 fitted components,244 nets,1125 connected endpoints and19 intentional NC pins;40 MPN groups.
- `electrical/glove-v3.kicad_sch`: native schematic; `electrical/glove-v3-routed.kicad_pcb`:90×60×1.6mm four-layer routing. Native reconciliation and KiCad DRC report zero violations, opens or footprint errors.
- `electrical/manufacturing/manifest.json`:18 hashed manufacturing files, Gerbers/drills,356-placement CPL and actual-board assembly drawings. VIPPO epoxy-filled, planarized, copper-capped vias are mandatory at34 SMD-overlap locations.
- `../../firmware/tactile_v3/`: compiled XIAO nRF52840 firmware,130688 bytes flash/21408 bytes static RAM; matching HEX/UF2/debug ELF and source hashes.
- `../../tools/tactile_v3/`: transport, recording and Bluetooth bridge. Wireprotocol2 explicitly records3V reference,1.25V midpoint and2.5V excitation.
- `guide/index.html`, `sensors/assembly.md`, `sensors/wiring.csv`:20 anatomical locations, film orientation, stack construction and six keyed harness branches.
- `enclosure/index.html`: existing500mAh core enclosure. `enclosure/pebble-concept/index.html`: separate rounded CAD concept with actual geometry and constraints; its106×82×34.56mm envelope is not a watch-size product. Camera/largerbattery integration is pending.
- `camera/runtime-and-integration.md`, `camera/runtime-budget.json`, `camera/camera-selection.md`: six-hour power ceiling, exact battery candidate, optics and heat checks, with sources.
- `procurement/jlc-v33/`: current quote files and exact-part availability/substitution records. The earlier V3.1/V3.2 quote artifacts are historical partial quotes.

## Verified in software and simulation

- `verification/final-software-v33.json`:488 distinct repository tests plus four subtests pass; JavaScript syntax passes.
- `verification/firmware-simulation.md`:41 actual-sketch scenarios pass ASan/UBSan, including acquisition, timing rollover, button, power qualification, malformed commands, transport faults, backpressure and IMU failures.
- `verification/signal-chain/piezo-end-to-end.md`:520 modeled ADC samples survive USB and BLE selected-channel transport exactly, with timestamps and six RMS/peak windows independently checked.
- `verification/power-simulation.md`: corrected reference, excitation buffer, shutdown/protection and component-current checks.
- `verification/analog-signal-chain.md`:16/18 primary Microchip/Nexperia transient cases complete; two late-recovery solver failures also complete with explicitly bounded1fF numerical stabilization. Seven TI mux/driver cases complete, informing6µs dynamic and12µs pressure waits.

These checks do not substitute for physical timing, radio, current, thermal or tactile characterization.

## Use of the tactile core

Hold the button0.8s from sleep and release to wake; continue to3s for a120s pairing window. While running, tap to pause/resume or hold1.5s to sleep after release. Blue indicates startup/pairing; green indicates ready/collecting; amber indicates low or unqualified battery; a red double flash indicates ADC trouble.

Target acquisition is20 vibration channels at4kS/s each and20 pressure channels at50S/s each. USB carries full raw data. BLE carries all-channel features or one selected raw channel plus IMU/health. Invalid-power and dropped-frame flags remain in recordings. The current battery configuration is a protected500mAh cell with100mA charging; it is not the six-hour camera system.

## Manufacturing and capability scope

The tactile board is a routed engineering prototype. Its specified VIPPO process, complete sourcing, assembly quote and first-article acceptance remain required. The camera integration changes the MCU/power/firmware design and enclosure; it is not yet a factory release. The initialUS$150–200 complete delivered target remains unverified. No purchase or email has been sent.

Pressure readings require cell calibration; vibration plots are signal measurements, not measured surface Ra. The hardware does not directly measure every finger joint or drift-free hidden-hand position. Rendering and demos must preserve those distinctions.
