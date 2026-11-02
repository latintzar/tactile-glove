# Module map

| Module | Entry points | Responsibility |
|---|---|---|
| Local design viewer | [`tools/serve.py`](../tools/serve.py), [`enclosure/viewer.html`](../hardware/glove-v4/enclosure/viewer.html), [`viewer.js`](../hardware/glove-v4/enclosure/viewer.js) | Loopback-only static exploration of generated engineering parts. |
| Main electronics | [`electrical/`](../hardware/glove-v4/electrical/), [`components.json`](../hardware/glove-v4/electrical/components.json), [`placement.json`](../hardware/glove-v4/electrical/placement.json) | Native main-board/schematic, MPN/designator/net mapping, routing and placement. |
| Power/interface contracts | [`power/`](../hardware/glove-v4/power/), [`interfaces/`](../hardware/glove-v4/interfaces/) | Rails, charger/battery, camera, SD, dual IMUs and physical connector contracts. |
| Dorsal hand tile | [`interfaces/hand-tile/`](../hardware/glove-v4/interfaces/hand-tile/) | Separate IMU PCB and its fabrication manifest. |
| Mechanical design | [`enclosure/`](../hardware/glove-v4/enclosure/) | Geometry generator, STLs, component/harness envelopes, viewer and independent nominal audit. |
| Assembly | [`guide/`](../hardware/glove-v4/guide/), [`glove-v3/sensors/`](../hardware/glove-v3/sensors/) | Material stack/cut patterns, twenty cells, keyed harness and factory acceptance. |
| Acquisition | [`core.hpp`](../firmware/tactile_v4/main/core.hpp), [`app.cpp`](../firmware/tactile_v4/main/app.cpp) | Sample scheduling, validity/overrun tracking, feature windows and peripheral orchestration. |
| Power/shutdown | [`shutdown.hpp`](../firmware/tactile_v4/main/shutdown.hpp), [`firmware guide`](../firmware/tactile_v4/README.md) | Qualification, button/pairing windows, rail sequence and shutdown ownership. |
| Packet/browser boundary | [`packet.hpp`](../firmware/tactile_v4/main/packet.hpp), [`http.cpp`](../firmware/tactile_v4/main/http.cpp), [`PROTOCOL.md`](../firmware/tactile_v4/PROTOCOL.md) | G3/COBS/CRC records, bounded commands, independent preview queue and delivery-loss counters. |
| Device UI | [`software-preview/`](../hardware/glove-v4/software-preview/), [`static/glove-viewer/`](../static/glove-viewer/) | Contact map, camera, waveform/spectrum, labels and status; bundled reference hand/Three.js. |
| Camera override | [`camera_override/`](../firmware/tactile_v4/camera_override/) | Hash-pinned Espressif camera changes for bounded waits and malformed-frame recovery. |
| Host verification | [`tools/tactile_v4/`](../tools/tactile_v4/), [`camera tests`](../firmware/tactile_v4/camera_override/tests/test_cam_take.py) | Actual C++ execution, packet decoding and driver control-flow checks. |
| Earlier camera-free design | [`glove-v3/`](../hardware/glove-v3/), [`firmware/tactile_v3/`](../firmware/tactile_v3/) | Sensor laminate and required V3 protocol/button headers, earlier routed board and manufacturing context. |

[Architecture](architecture.md) explains how these modules connect. [Setup](setup.md) gives the commands and recorded tool versions.
