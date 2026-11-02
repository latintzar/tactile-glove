> Current public snapshot: the reviewed USB correction is applied to the canonical 561-component board. Its SHA256 is `973111f03d52a0288c53378c9ba5df2dc6b7ac896ce2e6f88557ab0d7846a84b`; 20 unconnected items remain. Dated proposal receipts retain their original stage.

# V4 hardware coverage matrix

Generated from the 561-row V4 component manifest. This is an evidence map: static checks, electrical simulation/model proxies, host/firmware fixtures, and physical qualification are separate classes. It does not claim comprehensive actual-hardware simulation.

Manifest SHA256: `d40ec87d20b742582ac97d74a30e2f34d674a3f4e76253757d2bd8b04845ffd8`
Generator SHA256: `69baeab98394c6bced443049b1c512c6e9de23090065cffe8fc9650857753c18`

## Coverage by block

| Block | Components | Evidence classes | Current status |
|---|---:|---|---|
| tactile | 343 | static_check, simulation_model_proxy, host_firmware_fixture, physical_pending | model_proxy_and_host_fixture; physical qualification pending |
| power | 161 | static_check, simulation_model_proxy, physical_pending | static_and_partial_native_run; finite-impedance and physical qualification pending |
| camera | 37 | static_check, host_firmware_fixture, physical_pending | interface_and_wire_fixture; camera hardware qualification pending |
| imu | 5 | static_check, host_firmware_fixture, physical_pending | interface_and_native_fixture; IMU hardware qualification pending |
| sd | 15 | static_check, physical_pending | interface/source evidence; storage hardware qualification pending |

## Block boundaries

**tactile (343)** — Inherited V3 signal-chain and mux decks cover the reviewed topology and proxy loading. V4 differential ADC settling has five completed native cases. V4 rail coupling and physical sensor/cable behavior remain open.

**power (161)** — Power arithmetic and selected buck execution are evidenced. The finite-impedance rail qualification and thermal/physical behavior are open.

**camera (37)** — Interface arithmetic and framed browser fixture are covered; no camera capture or SI proof is claimed.

**imu (5)** — Register/interface checks and native raw/status framing are covered; sensor output and mechanical placement remain physical work.

**sd (15)** — Pin, footprint, and source evidence are recorded; card insertion, signal integrity, filesystem endurance, and thermal behavior remain physical work.

## Open release blockers

Design/quote gates apply before a first-article order. Measured physical acceptance applies before delivery as a tested working glove; it cannot be completed before the first unit exists.

| Blocker | Status | Evidence / detail |
|---|---|---|
| requested_size | blocking_first_article_order | Current assembly 112 × 105.6 × 47.1 mm and estimated 218.2–233.2 g before textile/harness exceed the preferred 50.8 × 38.1 mm footprint. A compact redesign or explicitly accepted dimensioned alternative is required; CAD clearance alone does not close this requirement. Evidence: hardware/glove-v4/enclosure/compact-size-options.md, hardware/glove-v4/system-contract.json |
| landed_cost_and_delivery | blocking_first_article_order | The requested $150–200 complete one-glove budget is unclosed. Exact assembled/printed/harness/sensor/battery cost, minimum quantities, shipping, VAT and delivery dates need a complete current quote; partial component subtotals do not satisfy it. Evidence: hardware/glove-v4/procurement/cost-status.md, hardware/glove-v4/procurement/bom-source-plan.csv |
| continuous_runtime | design_margin_and_delivery_blocker | The conservative 6.019 h calculation leaves about 1.16 minutes over the six-hour target. Changes to electronics/thermal design must update the budget. Delivery requires six-hour simultaneous camera/tactile/IMU/storage operation with recorded temperature, current, capacity and drop counters. Evidence: hardware/glove-v4/verification/energy-budget.json, hardware/glove-v4/guide/factory-record-template.json |
| physical_and_demo_acceptance | required_for_tested_delivery | First-article signal/calibration, camera, IMU, storage, radio, harness and wearable-fit checks remain unmeasured. The current reference hand mesh/contact display does not establish finger joint angles, precise hidden-hand position or calibrated roughness; the requested tracking/texture demo needs its own measured acceptance evidence. Evidence: hardware/glove-v4/guide/factory-flash-and-acceptance.md, hardware/glove-v4/guide/factory-record-template.json, hardware/glove-v4/README.md |
| routing_open_items | blocking | 20 unconnected items remain; the routing candidate DRC includes USB-net/pair work in the blocker scope. Evidence: hardware/glove-v4/electrical/remaining-nets.json, hardware/glove-v4/electrical/routing-progress.json, hardware/glove-v4/electrical/routing-candidate.drc.txt |
| mechanical_revision | current_nominal_geometry | Clearance evidence matches current component placement. Evidence: hardware/glove-v4/enclosure/clearance-report.json |
| coupled_analog | unresolved_solver | One complete conditioned63-amplifier native diagnostic; isolated tightening of gmin or abstol fails, so numerical qualification remains open. Evidence: hardware/glove-v4/verification/coupled-analog/results.json |
| rail_finite_impedance | ongoing | A corrected native buck run is recorded; full finite-impedance rail qualification remains open. Evidence: hardware/glove-v4/power/simulation/latest-runs.json, hardware/glove-v4/power/simulation/buck-results.json |
| usb_high_current_path | routing_and_thermal_open | The reviewed USB correction is applied to the canonical 20-open board in097093661f7aa7e29208f5f636a8289161d4f53e. U32 OUT is widened to0.6mm and U42 VBUS has the reviewed fanout/POWER_A extension. Full thermal qualification and remaining routing are open. Current evidence: hardware/glove-v4/verification/power-escape-review/manifest.json; predecessor finding: hardware/glove-v4/verification/routing-proposal20/usb-power-path.json |
| shutdown_fault_paths | blocking | Lost-source latch, bounded camera queue and owner-acknowledged checked shutdown are built/tested. Permanent peripheral/control-bus faults still need independent reset/power-off hardware; current firmware holds shutdown rather than asserting successful sleep. Evidence: firmware/tactile_v4/main/app.cpp, firmware/tactile_v4/main/storage.cpp |
| thermal | blocking | Thermal-resistance sensitivity calculations exceed contact/pack screening targets; the buffered temperature-readout and outward heat-path proposals have local evidence plus a native-tested isolated temperature policy; circuit and shutdown integration remain unapplied and continuous wear remains unqualified. Evidence: hardware/glove-v4/verification/thermal-screen/results.json |

## Reproduction

Run `python3 hardware/glove-v4/verification/build_hardware_coverage_matrix.py` from the repository root. The script checks the manifest count, unique refs/designators, exact subsystem counts, evidence existence, and the current routing source/board hashes and clearance-placement correspondence before writing the JSON and Markdown reports.

The full per-component one-to-one inventory, evidence paths, and SHA256 values are in `hardware/glove-v4/verification/hardware-coverage-matrix.json`.
