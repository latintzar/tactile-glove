# Product tour

Artisan Glove is a sensing-glove design for recording hand contact, vibration and video. Its source connects a physical sensing stack to the electronics, firmware, recording format and browser tools needed to inspect an acquisition.

## Explore one complete design journey

1. **Open the cuff.** Run `python3 tools/serve.py` from the repository root, then open `http://127.0.0.1:8070/`. Choose **Open** to see the main board, battery and camera, then **Exploded** to separate the housing and service parts. Select a component to inspect it. You are looking at dimensioned engineering geometry and component envelopes.
2. **Follow a sensing location.** Open the [visual assembly guide](../hardware/glove-v4/guide/assembly.html). Follow the [V3 sensor stack](../hardware/glove-v3/sensors/assembly.md), cut pattern and wire labels reused by V4. Each location has a pressure-sensitive film cell and a separate PVDF vibration channel.
3. **Trace the hardware.** Open the [main KiCad project](../hardware/glove-v4/electrical/glove-v4-routing-candidate.kicad_pro), [canonical routing candidate](../hardware/glove-v4/electrical/glove-v4-routing-candidate.kicad_pcb) and [schematic](../hardware/glove-v4/electrical/glove-v4.kicad_sch). Use component/reference and net maps to follow that location through its analogue front end and ADC. The [dorsal hand tile](../hardware/glove-v4/interfaces/hand-tile/) is a separate native design with fabrication outputs.
4. **Execute the acquisition logic.** Run the [host checks](setup.md#host-checks). The real C++ acquisition core processes modelled electrical samples, emits packets, and exposes timing/queue/error metadata. The Python and JavaScript decoders check those produced bytes. This gives you a reproducible software boundary before building electronics.
5. **Inspect the device experience.** Open `http://127.0.0.1:8070/device/`. The bundled monitor exposes a hand contact map, wrist camera, selected vibration waveform, spectrum, labels and acquisition health. It waits for actual cuff data. After hardware bring-up, the cuff serves this UI on its private Wi-Fi network; [firmware setup](../firmware/tactile_v4/README.md) explains Wi-Fi/BLE and packet channels.
6. **Prepare a physical build.** Use the [BOM](../hardware/glove-v4/procurement/micron-v4-board-bom.csv), [print manifest](../hardware/glove-v4/enclosure/print-manifest.json) and [factory acceptance guide](../hardware/glove-v4/guide/factory-flash-and-acceptance.md). Close main-board routing and process acceptance first, then measure actual timing, calibration, optics, thermals and endurance against the [status checklist](status.md).

## Product areas

| Area | Actions and results | Source |
|---|---|---|
| Design viewer | Assemble/explode, rotate and select actual generated parts; inspect envelopes and nominal fit. | [`enclosure/viewer.html`](../hardware/glove-v4/enclosure/viewer.html) and [`viewer.js`](../hardware/glove-v4/enclosure/viewer.js) |
| Assembly | Place twenty sensing pairs, fit the cuff and dorsal IMU, follow keyed harness branches. | [`guide/assembly.html`](../hardware/glove-v4/guide/assembly.html), [`sensors/`](../hardware/glove-v3/sensors/) |
| Main board and hand tile | Edit native circuits/placement/routing and use designator/MPN BOMs. | [`electrical/`](../hardware/glove-v4/electrical/), [`interfaces/hand-tile/`](../hardware/glove-v4/interfaces/hand-tile/) |
| Device monitor | Inspect contact, camera, selected waveform/spectrum, labels, battery and loss counters. | [`software-preview/`](../hardware/glove-v4/software-preview/), [`http.cpp`](../firmware/tactile_v4/main/http.cpp) |
| Acquisition and storage | Follow ADC scan timing, dual IMUs, camera ownership, timestamped packets and SD recording. | [`firmware/tactile_v4/main/`](../firmware/tactile_v4/main/), [`PROTOCOL.md`](../firmware/tactile_v4/PROTOCOL.md) |
| Reuse and verification | Run sanitizer cases, independent packet decoders and nominal STL audits. | [`tools/tactile_v4/`](../tools/tactile_v4/), [verification guide](verification.md) |

## Where to go next

[Setup](setup.md) gives the shortest working path. [Module map](module-map.md) locates the source. [Architecture](architecture.md) explains ownership and data flow. [Design history](design-history.md) explains the sensing stack, separate IMUs, camera correction and engineering tradeoffs. [Current status](status.md) tells you which evidence is already reproducible and which measurements a physical build needs.
