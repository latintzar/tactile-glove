# Historical target-build evidence

`build-manifest.json` records the original 2026-10-23 source/toolchain, successful target compile and artifact hashes. `SHA256SUMS` is the original historical artifact list; it also names files retained privately.

This source release includes native-generated test fixtures, compile/source/configuration records and flash descriptions. Target application/bootloader/partition images, ELF/map and build-log archives are retained privately pending complete binary-linked SDK notices. [Image omission hashes](../../../provenance/omitted-target-images.json) and [verification](../../../docs/verification.md) document that scope.

Use [setup](../../../docs/setup.md#esp32-s3-target-build) to build your own target with the pinned SDK. The native fixtures exercise software and packet boundaries; assembled-device acquisition, calibration, timing and endurance have their own acceptance steps.
