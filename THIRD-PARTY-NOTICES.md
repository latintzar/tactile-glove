# Third-party notices

Peter Neyra’s original source, hardware designs, docs and owned images use the root [MIT licence](LICENSE). The following redistributed material retains its own terms.

## KiCad footprint libraries — CC BY-SA 4.0

Project-local `.kicad_mod` library files copied or adapted from KiCad retain **CC BY-SA 4.0**. The pinned collections are `7ebfa6b23cc292a56f751b7b5f4a0e12eeef69dd` and `f8440fa61a5690b48b325c891fdb99c0038a5a59`. See [original notice 7ebfa6](LICENSES/KiCad-7ebfa6-LICENSE.md), [original notice f8440f](LICENSES/KiCad-f8440f-LICENSE.md) and [CC BY-SA legal code](LICENSES/CC-BY-SA-4.0.txt).

KiCad’s design-output exception permits a separate licence for boards/designs using the libraries. Redistributed original or modified library collections retain the library licence. Local adaptations include KiCad 7 syntax normalization, fab-layer/reference conversion and source-recorded package/land adjustments. Per-footprint origin/hash records live in the `footprint-sources.json` / `footprints-preparation.json` files beside the native libraries. Manufacturer-drawing transcriptions are separately identified there; the KiCad file format itself does not identify authorship.

## Seeed XIAO footprints — MIT

The two modified XIAO footprint variants derive from Seeed-Projects’ OSHW-XIAO-Series, pinned `503f3486bdf9d696b74edb5ac525cfa92f3ebd68`, ©2024 Seeed-Projects. Retain the [Seeed MIT notice](LICENSES/Seeed-XIAO-MIT.txt). Their 22 pad numbers/positions/sizes/shapes/layers match the pinned original; public/native preparation changes are recorded with the footprint source metadata.

## Espressif camera override and target dependencies — Apache 2.0 / MIT

`firmware/tactile_v4/camera_override/driver/{cam_hal.c,esp_camera.c}` derive from `espressif/esp32-camera` 2.0.16 and preserve Espressif copyright and **Apache 2.0**. Peter Neyra’s modifications bound queue/recovery waits and the public frame wait; the files carry modification notices and the [override guide](firmware/tactile_v4/camera_override/README.md) records exact upstream/reviewed hashes. [Apache 2.0](LICENSES/Apache-2.0.txt) and the original [override licence](firmware/tactile_v4/camera_override/LICENSE) are included.

The historical target build used ESP-IDF 5.4.2 and the dependency versions in [`dependencies.lock`](firmware/tactile_v4/dependencies.lock). ESP-IDF, camera, esp_jpeg and esp_tinyusb retain Apache 2.0; TinyUSB 0.21.0~2 retains MIT ©2012–2026 hathach. Their exact notices are included under [`LICENSES/`](LICENSES/). Build tools and separately obtained SDK/model downloads retain their upstream terms.

## Browser/hand assets and earlier V3 dependency

Bundled Three.js and the reference hand asset retain their original [Three.js notice](static/glove-viewer/three-LICENSE.txt) and [hand notice](static/glove-viewer/hand-LICENSE.txt). The earlier V3 firmware retains the [Waveshare notice](firmware/tactile_v3/WAVESHARE-LICENSE.txt). The reference hand is a contact-location visualization, distinct from calibrated joint/pose inference.

## Vendor references

Datasheets, downloaded publisher HTML and vendor simulation binaries are represented through original URLs/hashes and reading evidence in [`provenance/vendor-references.json`](provenance/vendor-references.json). Obtain them from their publishers under their own terms when reproducing the corresponding models or document-hash checks.
