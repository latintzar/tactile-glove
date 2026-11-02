# Verification

## Reproducible checks

[Setup](setup.md#host-checks) contains the commands. Fresh execution from this public candidate checks:

- **34 C++ core cases and 13 HTTP cases:** actual production logic compiled with ASan/UBSan and warnings as errors; scheduling/quality flags, ring transfers, commands, button/power states, packet output, queue bounds, deadlines and disconnect cleanup.
- **32 Python protocol/piezo cases:** independent decoding of actual produced fixture bytes, electrical sample values, timestamps, validity and feature windows.
- **9 camera driver cases:** actual reviewed `cam_take()` body compiled with C11 sanitizers and deterministic queue/tick/DMA stubs.
- **JavaScript wire checks:** actual core fixture, fragmentation, overflow recovery, CRC vectors, spectrum, JPEG CRC, RAW/features and loss counters.
- **17 static design server cases:** loopback URL, real geometry/assets, device-waiting page and path containment.
- **3 inventory-refresh cases:** scratch-Git edits preserve original provenance, track intentional changes/removals, reject outside symlinks and pass the actual package checker.
- **Independent STL audit:** actual emitted meshes and component/harness envelopes, separately from the generator’s pass flag. See the saved [audit](../hardware/glove-v4/enclosure/independent-stl-audit.json).

The C++/driver stubs model peripheral boundaries. Native timing inputs and electrical fixtures are explicit test inputs. Combined physical ADC/camera/radio/SD timing, optics, calibration, thermals and endurance belong to hardware acceptance.

## Dated target compilation

[`build-manifest.json`](../firmware/tactile_v4/artifacts/build-manifest.json) records the 2026-10-23 ESP32-S3 compile, source hashes, IDF/toolchain, dependency lock and binary/artifact hashes. The source candidate retains flash descriptions, SDK configuration, dependency lock, the historical checksum file and camera override record. Target/bootloader/partition images and private ELF/map/build-log archives remain outside this distribution until the complete binary-linked SDK notice closure is packaged. Their exact historical hashes remain in the dated manifest and [omission inventory](../provenance/omitted-target-images.json). Build your own target from the pinned source/SDK.

The original compiled C/C++ logic is preserved. Public redistribution adds explicit Apache modification-comment lines to the two camera files, updates the override/test hash pins, and curates docs/portable paths. Those public source hashes are recorded separately in the [public inventory](../provenance/public-files.json). The dated build manifest is historical rather than a claim that all current file bytes were recompiled. A fresh complete ESP32-S3 target build was not run for this packaging pass because the pinned SDK/toolchain is absent from the current environment; the reusable host checks run with ordinary local tools.

## Native hardware/manufacturing evidence

The public snapshot preserves the exact canonical V4 board, native schematics, footprints and 48 enclosure STLs. V3 and the V4 hand tile each have their own [manufacturing manifest](source-inventory.md). Their referenced files are checked by size/hash. The main V4 routing candidate is an engineering source, with 20 unconnected items remaining. Saved DRC/export tool records are distinguished from a newly executed KiCad run.

[Status](status.md) is the concise list of achieved evidence and remaining physical gates. Dated detailed records remain in their source modules.
