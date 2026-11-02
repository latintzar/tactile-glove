# Piezo waveform to host verification

The replay uses the actual complete `tactile_v3.ino` harness and the corrected canonical circuit: 531 pF PVDF plus 150 pF cable returning to GND, 100k input protection and BAV199 clamps. The complete SPICE transient places the 250 pC pulse at 80 ms; the 520-row fixture samples from 70 ms at 4 kHz. Pre-stimulus residual settling remains in the fixture. This is modeled electrical input, not measured contact force or texture.

- **520 USB scan codes match exactly**, using 11-byte stream fragmentation.
- **520 BLE RAW codes across 13 packets match exactly**, after signed conversion. Packet indexes and timestamps match their corresponding USB scans; period is 250 µs and the selected channel is 20.
- **Six complete 80-scan BLE feature windows pass** independent `isqrt(sum(code²)//80)` RMS and peak calculations. Every current RMS and peak is an exact match; the regression permits at most one RMS count.
- Window results `(index,RMS,peak)`: (0, 2695, 6096), (80, 1194, 2332), (160, 185, 352), (240, 40, 66), (320, 20, 25), (400, 18, 19).
- Version 2 health carries 3000 mV reference and 1250 mV midpoint. CRC decoding reports zero errors.
- Fixture SHA256: `92a8ea0e8100aa698586144a277f1971ae09d8190c4b560c5ba297f794af3d3b`.
- Sketch SHA256: `871ea438c9d609b9ccd9f50a4b58ffb8f2f1c4cfd93e0e6f24a54d1bfb2ea108`.

The machine-readable [result](piezo-end-to-end.json) includes source-manifest details and hashes of all four [actual firmware output streams](piezo-end-to-end/). Reproduce with `python3 tools/tactile_v3/test_piezo_end_to_end.py`. The matching 41-scenario ASan/UBSan run is retained in `tools/tactile_v3/firmware_sim/evidence/results.json`.

This verifies the executed firmware data path, framing, feature arithmetic and host decoding. Physical sensor response, MCU throughput and radio performance require their separate validation.
