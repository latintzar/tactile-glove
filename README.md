# Artisan Glove

Artisan Glove is a precision glove design for recording surface texture, contact and video.

[Website](https://atelierneyra.com/hardware/tactile-glove) · [Documentation](https://docs.atelierneyra.com/tactile-glove/overview/)

![Thin white nitrile precision glove recording surface texture, with its green cuff tab and hand-facing camera](https://atelierneyra.com/hardware/tactile-glove/media/precision-20261103/texture.webp)

The glove lets people collect touch data while they work. Contact-vibration sensors record the response as fingers move across a surface; pressure readings and video add context.

Twenty sensing locations combine pressure-sensitive film and PVDF vibration sensors. Two IMUs distinguish wrist/camera motion from the hand; an ESP32-S3 records timestamped streams and camera frames to microSD, with USB, Wi-Fi and a browser monitor for inspection. It is a reusable engineering project for people building tactile capture hardware, signal-processing experiments and wearable acquisition systems.

## Get the design

[Explore CAD](https://atelierneyra.com/hardware/tactile-glove/viewer/) · [Product tour](docs/product-tour.md) · [Native PCB](hardware/glove-v4/electrical/glove-v4-routing-candidate.kicad_pcb) · [Enclosure parts](hardware/glove-v4/enclosure/)

[Setup](docs/setup.md) covers local inspection and the reusable firmware and hardware files.

## What you can explore

| Area | What you can do |
|---|---|
| Cuff design | Inspect the enclosure geometry, camera, battery, connectors, component envelopes and individual parts. |
| Sensing glove | Follow the twenty pressure/PVDF locations, material stack, cut patterns and keyed harness. |
| Electronics | Edit the native KiCad main board and schematics, dorsal IMU tile, footprints, component lists and net mappings. |
| Firmware | Inspect acquisition timing, bus ownership, power transitions, camera deadlines, storage, packet formats and the device browser UI. |
| Verification | Execute the production C++ core and HTTP logic on your computer, decode their actual output, and audit STL clearances. |
| Earlier experiments | Read the Bela sensing pilot and the earlier camera-free V3 board, with their achieved results and open questions kept explicit. |

## Current stage

This is a **source beta and engineering design in progress**. The ESP32-S3 target image was compiled; fresh host checks execute 34 core cases, 13 HTTP cases, 32 protocol/piezo cases and 9 camera-driver cases. The current 561-component V4 board has **20 unconnected items and zero saved physical DRC errors**. Its dorsal IMU tile includes fabrication outputs; the main board awaits routing and manufacturing qualification.

An assembled V4 glove, simultaneous acquisition/camera/radio timing, force calibration, enclosure acceptance and six-hour endurance remain physical validation steps. Rates below describe implementation settings and design targets. [Status and evidence](docs/status.md) distinguish each stage.

The thin-glove appearance and surgery/sport scenes are design studies. The [website's sensing view](https://atelierneyra.com/hardware/tactile-glove#sensing) illustrates the twenty documented locations using the same hand photograph. [Design history](docs/design-history.md) records the native V4 geometry and actual validation stage.

| Stream | Implementation setting |
|---|---|
| Pressure | 20 locations × 50 samples/s; electrical levels until per-cell force calibration |
| PVDF vibration | 20 locations × 4,000 samples/s |
| Motion | Two ISM330DHCX IMUs at 833 Hz |
| Camera | OV5640 VGA JPEG, approximately 10 fps target |
| Recording | Timestamped, checksummed tactile/motion streams and JPEG frames on microSD |
| Connections | USB and Wi-Fi full streams; BLE setup, status and selected data |

## Get started

Python 3.11 or later is enough to open the static design viewer:

```sh
git clone https://github.com/latintzar/tactile-glove.git
cd tactile-glove
python3 tools/serve.py
```

Open **http://127.0.0.1:8070/**. The viewer loads the supplied engineering geometry locally. [Setup](docs/setup.md) covers host tests, native KiCad editing, enclosure checks and the pinned ESP-IDF firmware build. Device assembly and programming have their own acceptance guide.

## Source and guides

- [Product tour and complete journey](docs/product-tour.md)
- [Module map](docs/module-map.md) · [Architecture](docs/architecture.md)
- [Setup](docs/setup.md) · [Verification](docs/verification.md)
- [Current status](docs/status.md) · [Design history and decisions](docs/design-history.md)
- [V4 hardware guide](hardware/glove-v4/README.md) · [Firmware and protocol](firmware/tactile_v4/README.md)
- [Earlier Bela experiment](docs/bela-experiment.md)
- [Contributing and refreshing the inventory](CONTRIBUTING.md)
- [Source inventory and redistribution scope](docs/source-inventory.md) · [Third-party notices](THIRD-PARTY-NOTICES.md)

## Licence and credits

Peter Neyra’s original code, documentation and hardware design are [MIT licensed](LICENSE). Redistributed KiCad library files retain **CC BY-SA 4.0** with KiCad’s design-output exception; Espressif camera sources retain **Apache 2.0**; Seeed and viewer assets retain their own MIT notices. [Third-party notices](THIRD-PARTY-NOTICES.md) identify those boundaries and source revisions.

Made by [Atelier Neyra](https://atelierneyra.com/).
