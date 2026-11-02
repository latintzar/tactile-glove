# Artisan right-hand capture glove — V4

Open the [local design viewer](../../docs/setup.md#design-viewer) to inspect the cuff, or follow the [assembly guide](guide/assembly.html). This public package preserves the engineering source and dated checks; [current status](../../docs/status.md) identifies the remaining physical and manufacturing work.

This is the current complete-camera design. The V3 tactile circuits and glove laminate are retained inside V4; V3 manufacturing files describe the earlier camera-free board.

The factory assembles and programs the cuff electronics, camera, battery, card and keyed harnesses. The wearer fits twenty prepared pressure/PVDF locations to the glove and plugs in the labeled branches. A local phone/laptop viewer shows contact, vibration, camera frames and acquisition status; the card retains full recordings.

| Function | Current implementation |
|---|---|
| Contact | 20 independent Velostat/Linqstat locations, 50 samples/s each; electrical levels until force calibration |
| Texture signal | 20 independent PVDF locations, 4,000 samples/s each; raw waveform, RMS/peak and spectrum |
| Cuff/camera motion | ISM330DHCXTR on the main PCB, 833 Hz |
| Hand motion | Separate 16×16 mm ISM330DHCXTR tile on the back of the hand, 833 Hz; keyed four-wire cable |
| Camera | CamThink 73.002.000035, OV5640, 120° diagonal field, 8 cm preset focus; VGA JPEG around 10 fps |
| Controller | ESP32-S3-WROOM-1-N8R8; USB-C; one button; RGB indicator |
| Communications | BLE setup/status/selected preview; Wi-Fi camera/full data and browser viewer; USB data |
| Recording | Kingston SDCIT2/32GB; timestamped checksummed streams and take labels |
| Battery | Protected Jauch 250480, 6.5 Ah minimum, 3.6 V; separate pack thermistor |

Two IMUs distinguish cuff/camera motion from the hand moving at the wrist. Joint angles and absolute hidden-hand position require their own tracking estimates and calibration. The current viewer uses a reference hand mesh; its colored sensing locations represent incoming contact measurements.

The six-hour continuous target has a 6.019-hour conservative energy scenario. The physical unit must pass the documented six-hour recording, temperature, card-capacity and rail tests. Radio throughput, force calibration and texture recognition depend on measured hardware/data evidence.

## Hardware verification —23 October

The [hardware evidence matrix](verification/hardware-coverage-matrix.md) inventories all561 fitted components and separates source/geometry checks, circuit models, firmware tests and physical qualification. The expanded [differential ADC simulation](verification/differential-adc/README.md) found a pressure-settling error; the actual firmware now waits24 µs for pressure and6 µs for acoustic samples. Five native cases pass the modeled settling criterion, and the corrected target image has been compiled and checked.

The [thermal screen](verification/thermal-screen/README.md) identifies heat-path and battery-mode temperature-readout work. [Combined20-channel analog runs](verification/coupled-analog/README.md) now retain one complete conditioned diagnostic with unresolved numerical sensitivity; [finite battery-path converter runs](power/battery-path-transient-review.md) still have numerical completion failures. These retain their native evidence and cannot count as full-system validation. Routing and final assembly release remain open.

## Files to use

- [System contract](system-contract.json): selections and remaining release work.
- [Visual assembly guide](guide/assembly.html) and [sensor/harness guide](guide/README.md).
- [Factory flashing and acceptance](guide/factory-flash-and-acceptance.md), [fillable acceptance record](guide/factory-record-template.json).
- [Main electrical source](electrical/components.json), [native schematic](electrical/glove-v4.kicad_sch), [pin/net reconciliation](electrical/native-net-reconciliation.json).
- [Dorsal hand tile](interfaces/hand-tile/): separate routed PCB and fabrication files.
- [Interactive cuff CAD](enclosure/viewer.html) and [enclosure specifications](enclosure/README.md): generated geometry, component-placement source and clearance evidence.
- [Two-IMU placement drawing](guide/dual-imu.svg): hand tile, cuff sensor and keyed cable.
- [Component/BOM source plan](procurement/bom-source-plan.csv), [main-board BOM](procurement/micron-v4-board-bom.csv) and [public sourcing scope](../../docs/source-inventory.md).
- [Power simulations](power/simulation/buck-results.json), [energy calculation](verification/energy-budget.md), [storage calculation](guide/storage-budget.json).
- [Firmware artifacts](../../firmware/tactile_v4/artifacts/) and [reproducible verification](../../docs/verification.md).

Main-board routing is active release work. The enclosure reports bind their clearance result to a particular component-placement hash; the current hardware matrix checks that correspondence. The published mechanical snapshot passed nominal CAD/STL checks; the rigid case is 112×104×45.5 mm, or 112×105.6×47.1 mm including the sheet window and flat carrier, with an estimated cuff mass of 218.2–233.2 g before external textile/harness. The preferred 50.8×38.1 mm footprint requires a different electronics/battery layout; [size audit](enclosure/compact-size-options.md) records the actual limits. [JLC3DP fabrication plan](procurement/jlc3dp-enclosure.md) separates printed shells from precision, optical and elastomer parts; process acceptance remains open. The exact assembled landed price is pending; the original $150–200 total is not established. Historical price observations and partial subtotals are identified as such. Supplier qualification and physical purchasing are separate project steps.

The2026-10-23 [shutdown review](verification/shutdown/README.md) corrected lost-supply handling, camera queue deadlines and premature rail shutdown. The local ESP32-S3 target build,34core+13HTTP sanitizer cases and9camera-driver cases pass. The phase fault matrix verifies owner acknowledgements and retry ordering; permanent driver/bus failures still require the independent hardware-reset design. The [temperature-readout/heat-path proposal](verification/thermal-screen/readout-proposal/README.md) has completed local model runs and clearance checks, with its remaining error/thermal bounds recorded explicitly. Those circuit and mechanical changes are still unapplied.

The [USB power-escape review](verification/power-escape-review/README.md) records the reviewed 20-open USB correction, applied to the canonical board in `097093661f7aa7e29208f5f636a8289161d4f53e`. It widens U32 OUT to 0.6 mm and connects U42 VBUS through a short fanout and a verified extension of POWER_A. Its calculated USB positive-copper resistance falls from 51.484 to 35.640 mΩ under the recorded assumptions; all 561 components and their pin mappings are preserved. Full thermal and remaining routing closure remain open. The [earlier review](verification/routing-proposal20/ARCHIVE-STATUS.md) retains the predecessor archive and findings. The current canonical board has 20 unconnected items, zero physical DRC errors and 561 components. The saved candidate archive and earlier 24-open descriptions are historical evidence; [current status](../../docs/status.md) binds these facts to the actual native board hash.

The [same-capability cost reduction](value-engineering/README.md) targets one-third of complete one-glove delivered cash cost. The first sourcing/model screen retains the full requirement lock, rejects shorter-runtime and failed-settling alternatives, and leaves both complete quote totals and qualification gates open.


The latest [temperature-policy implementation](verification/thermal-screen/readout-proposal/firmware/README.md) passes254 deterministic assertions and100,000 seeded ADC input checks under ASan/UBSan. It remains isolated from the target until the two-NTC circuit and load-control integration are applied. [Converter backend diagnostics](power/finite-path-backend-diagnostics/README.md) retain the final bounded ngspice failures and vendor simulator requirement. Repository checks after this work:516 tests and4 subtests passed; `node --check static/app.js` and `git diff --check` passed. These checks leave the manufacturing, numerical convergence and physical acceptance gates open.
