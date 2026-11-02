# Design history and decisions

## Earlier Bela sensing experiments

The earlier work used physical piezo recordings to study vibration and surface roughness. A controlled saved-clip pilot produced useful traces and held-out results, then sustained live P60/P220 testing disagreed with the saved-clip evaluation. That result exposed the need to control mounting, gain, force and movement. [Experiment evidence](bela-experiment.md) preserves this distinction.

## Camera-free V3

V3 established twenty paired pressure/PVDF sensing locations, a soft laminate, labelled wiring and a routed camera-free electronics design. The source includes its actual native board, fabrication files, cut pattern and assembly guide. V4 keeps those sensing and protocol/button dependencies; V3 fabrication outputs identify their own earlier revision.

## Camera and two motion references in V4

V4 combines tactile signals with wrist video and two IMUs. A hand IMU and a cuff/camera IMU provide separate motion references across wrist movement. A reference hand mesh is useful for showing contact locations; calibrated joint angles and absolute hidden-hand tracking require additional estimation/calibration.

The camera influences pin allocation, power rails, PSRAM ownership, recording capacity, antenna placement and enclosure size. Those constraints led to the dimensioned 112×104×45.5 mm cuff rather than the smaller appearance concept. [Size options](../hardware/glove-v4/enclosure/compact-size-options.md) explain the tradeoffs.

## Bounded acquisition and recoverable faults

Explicit core/driver/queue ownership keeps a slow browser or camera consumer from holding the acquisition buffer. Native tests exercise actual packet output, malformed camera recovery, preview loss accounting and shutdown ordering. The [shutdown review](../hardware/glove-v4/verification/shutdown/README.md) records why supply loss, deadlines and acknowledgements needed corrections.

## Analogue settling correction

Differential ADC simulation exposed pressure settling error. The current firmware uses 24 μs pressure and 6 μs acoustic settling. [Simulation evidence](../hardware/glove-v4/verification/differential-adc/README.md) and actual core fixtures connect that circuit model to decoded packets. Electrical stimulation and measured force/texture classification remain separate evidence classes.

## Applied USB correction and remaining routing

The reviewed USB power-escape candidate was applied to the canonical board in `097093661f7aa7e29208f5f636a8289161d4f53e`. It widens U32 OUT and connects U42 VBUS while retaining the 561-component mapping. The current board has 20 remaining unconnected items. [Review](../hardware/glove-v4/verification/power-escape-review/README.md) preserves the resistance calculation and checks; earlier archives retain their original baseline/candidate status.

## Thermal and cost proposals

The heat-path/temperature-readout proposal is separate and unapplied. The value-engineering work preserves the full sensing, camera, recording, protection and six-hour target requirements while testing possible cost reductions. Detailed [thermal evidence](../hardware/glove-v4/verification/thermal-screen/README.md), [proposal](../hardware/glove-v4/verification/thermal-screen/readout-proposal/README.md) and [cost decisions](../hardware/glove-v4/value-engineering/README.md) retain their assumptions and unresolved bounds.
