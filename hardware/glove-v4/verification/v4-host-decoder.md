# V4 host wire decoder verification

Updated 22 October 2026. The host decoder is `tools/tactile_v4/protocol.py`.

## Current checks

`python3 -m pytest -q tools/tactile_v4/test_protocol.py tools/tactile_v4/test_piezo_e2e.py`: **32 passed**. The delivered firmware image is unchanged by this host-only correction. Exact current host source hashes are in `firmware/tactile_v4/artifacts/verification-summary.json`.

- G3 protocol version2 uses little-endian fields, COBS framing, CRC16-CCITT and sequence counters. The decoder bounds corrupt input, retains gaps and recovers at frame boundaries.
- Kind6 validates its24-byte metadata header and seven-byte tagged FIFO words. Source0 is cuff/0x6A; source1 is hand/0x6B. Both declare833Hz, ±4g and ±1000degrees/s. Original words, including counter/parity bits, remain available byte-for-byte.
- Gyro/accelerometer words expose signed raw axes and nominal physical units. Per-unit calibration remains explicitly unavailable. Unknown accelerometer ranges are rejected.
- Kind7 decodes32bytes of bootID, camera/IMU/capture/card counters and state flags; kind8 validates the13-byte take label; kind9 decodes the two browser-loss counters.
- A sensor tick is25microseconds; signed modulo32-bit arithmetic maps sensor ticks to the MCU anchor and retains its timing uncertainty. Negative mapped times are rejected. These anchors alone do not reconstruct a continuous sample sequence after data loss.
- GV4J validates its32-byte header, first-DMA timestamp origin, JPEG length and both CRCs. Fragmented/coalesced input, sequence wrap/gaps and malformed records are covered.

## Manufacturer sensitivity correction

[ST DS13012 Rev7, Table3, page10](https://www.st.com/resource/en/datasheet/ism330dhcx.pdf) specifies **35mdps/LSB** at±1000degrees/s. Dividing1000 by32768 would give30.5176mdps/LSB and understate angular velocity by12.81%. The host now uses the published sensitivity table for all supported gyro and accelerometer ranges. At±4g, the nominal conversion is0.122mg/LSB.

Independent manufacturer-derived vectors check every supported scale. For example1000 gyro counts become35degrees/s at the configured range. Scale conversion preserves the original integers and does not imply a measured bias, temperature correction, camera extrinsics or verified tracking accuracy.

## Fixture scope

Tests decode real compiled-core fixtures for scan data, both IMUs, status, take labels and JPEG framing, plus the retained SPICE-to-firmware stimulus. These exercise software formats and signal conversion. Manufactured-sensor calibration, radio throughput and tracking performance remain factory/physical checks.

The current browser hand is a reference mesh colored by pressure. IMU packets are recorded and their presence is displayed; the browser has no orientation or absolute-position estimator yet.
