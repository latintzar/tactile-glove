# Setup

## Design viewer

Use Python 3.11 or later. From the repository root:

```sh
python3 tools/serve.py
```

Open `http://127.0.0.1:8070/`. The server binds to your local loopback interface and serves the supplied static files. **Assembled**, **Open**, **Exploded**, component selection and rotation use the actual generated enclosure geometry. `http://127.0.0.1:8070/device/` opens the device monitor in its hardware-waiting state. The design viewer needs a WebGL-capable browser; its assets are bundled locally.

## Host checks

Install a C++17 compiler (`g++`), Node.js 22 or later, and Python 3.11 or later. Create your own environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-test.txt
python tools/tactile_v4/run_native.py --output /tmp/tactile-v4-native
python -m pytest tools/tactile_v4/test_protocol.py tools/tactile_v4/test_piezo_e2e.py tests/test_local_server.py tests/test_inventory_refresh.py -q
python firmware/tactile_v4/camera_override/tests/test_cam_take.py
node --experimental-default-type=module tools/tactile_v4/test_web_wire.mjs
```

The native harness compiles the actual production core and HTTP implementation with ASan/UBSan. Tests use labelled model/fixture inputs; [verification](verification.md) describes the physical boundaries.

## Native electronics

The recorded schematic and manufacturing export tool is **KiCad 7.0.11+dfsg-1build4**. That version comes from native XML and Gerber headers. Open the project and select the current board:

- Main project: [`hardware/glove-v4/electrical/glove-v4-routing-candidate.kicad_pro`](../hardware/glove-v4/electrical/glove-v4-routing-candidate.kicad_pro).
- Canonical board: [`glove-v4-routing-candidate.kicad_pcb`](../hardware/glove-v4/electrical/glove-v4-routing-candidate.kicad_pcb).
- Hand tile: [`hardware/glove-v4/interfaces/hand-tile/`](../hardware/glove-v4/interfaces/hand-tile/).

Project-local footprint tables and libraries are included. Keep those files and their [licences](../THIRD-PARTY-NOTICES.md) together. The earlier V3 routed board/manufacturing set is a separate camera-free design. Review current [routing and fabrication status](status.md) before ordering hardware.

## Enclosure checks and regeneration

The supplied STLs and viewer work directly. The independent audit also verifies five manufacturer PDFs against the recorded hashes. First fetch the five `hardware/glove-v4/enclosure/sources/*.pdf` references listed with exact publisher URLs in [`vendor-references.json`](../provenance/vendor-references.json), checking each SHA256. Then run the mesh/clearance audit:

```sh
python -m pip install -r requirements-cad.txt
python hardware/glove-v4/enclosure/verify_enclosure.py
```

This writes `independent-stl-audit.json` beside the STLs. It checks actual meshes, component envelopes, service routes and nominal assembly contact. Run geometry generation in a scratch copy when editing the design:

```sh
python hardware/glove-v4/enclosure/generate_enclosure.py
```

The original generator also hashes six manufacturer reference documents. The public package retains their original URLs/hashes in [`provenance/vendor-references.json`](../provenance/vendor-references.json). For full regeneration, download the matching documents from their original publishers into the referenced `sources/` paths, verify their hashes, and keep those downloaded files private unless their redistribution terms allow sharing. The detailed [enclosure guide](../hardware/glove-v4/enclosure/README.md) records dimensions, processes and acceptance limits. The simulator records use ngspice 42 with XSPICE/PSpice compatibility; third-party model downloads and their terms are separate dependencies.

## ESP32-S3 target build

The dated successful build used **ESP-IDF 5.4.2** (`f5c3654a1c2d2a01f7f67def7a0dc48e691f63c0`), **xtensa-esp-elf-gcc 14.2.0** (`esp-14.2.0_20241119`), CMake 3.30.5 and Ninja 1.13.2.git.kitware.jobserver-pipe-1. The component lock records camera 2.0.16, JPEG 1.3.1, esp_tinyusb 1.7.6 and tinyusb 0.21.0~2.

Install and activate that SDK/toolchain through Espressif’s official tooling, then compile:

```sh
idf.py -C firmware/tactile_v4 -B build/tactile-v4 build
```

The local camera override checks exact upstream driver hashes. Its public files add explicit Apache modification comments; [source provenance](source-inventory.md) distinguishes them from the original dated build. The supplied manifest and historical image hashes are target-compilation evidence; target images are retained privately pending their complete binary-linked SDK notices. Build your own image for your hardware revision, complete [factory acceptance](../hardware/glove-v4/guide/factory-flash-and-acceptance.md), and deliberately select the correct device before programming.

## Connecting hardware

After qualified hardware bring-up, the cuff serves its monitor at `http://192.168.4.1/` on its own Wi-Fi network. BLE setup uses a physical pairing window and encrypted bonds; each device has its own generated Wi-Fi key. Full tactile streams use USB/TCP/SD; BLE and the browser carry selected preview/status data. Follow [firmware behaviour](../firmware/tactile_v4/README.md) and [packet definitions](../firmware/tactile_v4/PROTOCOL.md) for your client. The static design viewer and host checks use local files and require only your computer.
