# V4 firmware verification

This is a compiled engineering prototype for ESP32-S3-WROOM-1-N8R8. Source execution and target compilation establish the software evidence below. A populated cuff is still required to measure acquisition deadlines, radio and storage throughput, camera cadence, electrical behavior, heat and six-hour runtime.

## Executed checks

`tools/tactile_v4/run_native.py` compiles the production core and the exact production HTTP implementation with ASan, UBSan and compiler warnings treated as errors. Current saved result:34 core cases and13 HTTP cases pass. The instrumented HTTP boundary replaces sockets, RTOS queues and IDF entry points; it does not emulate the ESP32 radio or scheduler.

The core executes4000 scans over one modeled second:80,000 dynamic samples,1000 pressure samples and50 feature windows. Additional checks cover injected ADC failures/unqualified zeros, queue overflow and index rollover,100,000 concurrent ring transfers, button/pair behavior, power hysteresis, dual-IMU source/scale/timestamp metadata,512-record FIFO bounds, command validation/session reset, labels and JPEG CRC/header fields.

The same `CapturePackets` class used by the target task emits50 feature packets plus100 selected-RAW packets while RAW mode runs for one second. USB/TCP/SD/browser retain the features; BLE retains the selected waveform mode. Returning to FEATURES restores BLE feature delivery. The actual produced packet stream is retained as `artifacts/native-actual-core.bin.dual-mode`.

The physical-circuit SPICE fixture supplies520 channel0 ADC samples through the production acquisition/feature core. Independent Python decoding checks every raw code, timestamp, quality flag and all six complete RMS/peak windows. This fixture represents electrical stimulation; force and material recognition remain separate physical validations. The current combined host decoder/piezo result is32 passing tests.

The HTTP tests execute its actual queue admission, packet framing, latest-JPEG references, disconnect/reconnect cleanup, command parsing, static route lookup, Origin checks and200ms send deadlines. They inject partial writes, blocked sockets, queue overflow, oversized/fragmented/invalid commands and a full command mailbox. Scans are excluded before the browser sequence advances. Kind9 exposes queue/send/disconnect losses and unsent-preview replacement losses, with exact native assertions and a produced fixture. Separate browser queues preserve SD/TCP ownership.

## Target evidence

`artifacts/build-manifest.json` records the exact source hashes, generated web asset hashes, dependency lock, ESP-IDF revision, compiler, binary and compressed ELF/map/build log. The IRAM audit checks the compiled capture/timer call targets and rejects flash or atomic-lock helpers in those functions. It does not estimate real interrupt latency or prove a250µs scan deadline.

The dated build manifest records the original target compile. This public package retains its firmware images and dependency/source hashes, while private ELF/map/build-log archives remain outside the release. See [verification](../../docs/verification.md) for the exact distributed files and fresh checks. Device programming is a separate physical step.

## Implementation limits

- The camera's checked nominal timing is54MHz SYSCLK /2060HTS /2622VTS =9.99756fps. Actual cadence, exposure offset and dropped driver frames require measurement. Output pacing retains actual first-DMA timestamps.
- Native ADC durations are injected. Physical SPI/mux settling, interrupt scheduling and mixed camera/Wi-Fi/BLE/SD load remain unmeasured. Every acquired frame retains the mux-settling-unverified quality flag.
- The browser has64 packet slots in PSRAM and shares a latest JPEG reference. Queue gaps and camera sequence gaps expose preview losses. The200ms send deadline bounds one frame, not total browser refresh latency.
- Internal heap/stack margins and PSRAM use need measurement with all peripherals active. Task creation and allocation failures are checked; a successful link cannot establish runtime memory sufficiency.
- BLE uses encrypted bonds and a physical pairing window with Just Works pairing. Factory setup needs a per-device Wi-Fi credential/QR label or a supported HTTPS Web Bluetooth setup page. The local HTTP viewer operates after joining the cuff network.
- Continuous recording requires a suitable mounted microSD card. The software preserves explicit drop/fault metadata; sustained throughput and graceful recovery from card removal/full/stalled writes require hardware testing.
