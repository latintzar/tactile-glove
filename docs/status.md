# Engineering status

## Current V4 source

The public release supplies reproducible target source, host fixtures and historical compile/hash evidence. Target images remain in private custody until their complete binary-linked SDK notice closure is packaged.

The source snapshot comes from `f40271c6331db255bce6df60d84f0953fbe18355`, after the reviewed USB correction was applied in `097093661f7aa7e29208f5f636a8289161d4f53e`. It preserves native engineering assets, implementation and dated evidence.

| Part | Achieved evidence | Next physical or release step |
|---|---|---|
| Main PCB | 561 components, eight layers, 100×80 mm; canonical board SHA256 `973111f03d52a0288c53378c9ba5df2dc6b7ac896ce2e6f88557ab0d7846a84b`; saved zero physical DRC errors, 20 unconnected items and 87 warnings. | Finish routing, review warnings/stackup/assembly and obtain manufacturing qualification. |
| Hand IMU tile | Seven components, 16×16 mm; saved zero DRC errors/unconnected items; native source and 16 hashed fabrication files. | Fabricate, assemble and perform first-article electrical/mechanical acceptance. |
| Enclosure | Generator, 48 STLs, scene and component placement; nominal mesh/clearance audits and process requirements. Rigid case 112×104×45.5 mm; overall model envelope 112×105.6×47.1 mm. | Accept print/cast/cut processes and tolerances; inspect switch, window, glands, gasket, mounting, heat and assembled fit. |
| Firmware | Dated ESP32-S3 compile; host execution of 34 core, 13 HTTP, 32 protocol/piezo and nine camera-driver cases. | Program an accepted assembled unit; measure actual ADC/interrupt timing, mixed-load heap, camera/radio/SD performance and fault behaviour. |
| Sensing | Per-channel raw electrical capture, feature calculation, timestamps, labels and loss/quality flags implemented. | Calibrate force and measure cross-talk, movement artefacts, material/texture models and repeatability on physical hardware. |
| Battery/runtime | A conservative 6.019-hour energy scenario supports the six-hour target. | Measure six-hour recording, temperature, rail/load response and storage capacity on the complete unit. |
| Earlier Bela pilot | Actual recorded piezo traces; saved-clip evaluation and a documented live mismatch. | Improve mount/gain/controls and test held-out live behaviour separately from V4 assembly. |

## Current and historical descriptions

The canonical current board is the **applied 20-open board**. Dated routing/proposal archives record the earlier 24-open baseline or an isolated candidate; their dates and original observations remain useful history. The current overview and coverage note point to the actual canonical board above. The thermal/readout proposal is a separate, unapplied engineering proposal.

The compact campaign image is a **product concept**. The native viewer shows the actual dimensioned engineering enclosure. Saved firmware tests establish software behaviour; physical performance measurements belong to the assembled-device acceptance record.

## Release checklist

- Close the remaining 20 main-board connections and review all saved warnings.
- Bind the final routing/placement to enclosure fit and manufacturing exports.
- Obtain supplier/process acceptance for assembly, window bonding, elastomers and small parts.
- Assemble and inspect the cuff, sensing laminate, keyed harness and dorsal tile.
- Measure signal/timing/calibration, combined camera/radio/SD performance, faults and battery/thermal endurance.

Detailed evidence: [hardware coverage matrix](../hardware/glove-v4/verification/hardware-coverage-matrix.md), [USB correction](../hardware/glove-v4/verification/power-escape-review/README.md), [firmware verification](../firmware/tactile_v4/VERIFICATION.md) and [enclosure acceptance](../hardware/glove-v4/enclosure/README.md).
