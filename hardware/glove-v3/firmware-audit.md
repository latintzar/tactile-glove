# Tactile v3 firmware adversarial audit

Read-only review of `firmware/tactile_v3/tactile_v3.ino`, the G3 protocol header, the host bridge, and the cached Seeed XIAO nRF52840 Sense variant. This is a source audit; it is not a board validation result.

## Fix first

1. **HIGH — one global packet sequence makes BLE health report false drops.** `packetSequence` is shared by USB and BLE (`tactile_v3.ino:149-155`, `323-329`). Every USB scan increments it before the corresponding BLE feature/raw packet. A BLE feature stream therefore sees sequence jumps of roughly 80 scan packets per 80-scan window, and selected raw sees jumps of roughly 40. The bridge correctly reports these as `health.gaps` (`tools/tactile_v3/bridge.py:50-55`). Use independent sequence counters per transport, or define the sequence as an acquisition sequence carried unchanged into each transport packet.

2. **HIGH — the UI “deadline” guard is currently unconditional.** `uiDeadline(uint32_t)` returns `true` for every budget (`tactile_v3.ino:215`). `serviceUi()` can therefore perform button I2C, a battery `analogRead()`, and OLED transfers immediately before foreground work (`193-212`). At 400 kHz, an OLED address transaction with four control bytes and a four-byte data transaction are each over 100 µs on the wire before software overhead; the ADC battery read has no bounded timing contract here. The TIMER4 ISR is intended to preempt foreground work, but Wire/Arduino critical sections and the foreground drain workload still need measurement; the actual risk is capture latency, ring drain starvation, or bus contention. Implement a real elapsed-time guard or schedule UI only from a measured idle budget.

3. **HIGH — IMU FIFO service is admitted despite the disabled budget.** `loop()` calls `readImuFifo()` whenever `uiDeadline(300)` returns true (`tactile_v3.ino:469-475`), and `readImuFifo()` may execute eight separate 7-byte I2C reads (`132-145`). At 400 kHz this is a multi-hundred-microsecond to millisecond foreground burst, while the 4 kHz ISR continues to acquire. The code emits only the latest gyro/accel state in one IMU packet (`165-170`), so FIFO words drained during the burst are collapsed. Measure each `Wire` transaction on hardware and either drain with a bounded budget/interrupt/DMA design or expose explicit FIFO overflow/staleness counters.

4. **HIGH — ADC CNV/read timing remains an unverified assumption.** The ISR performs 20 dynamic conversions and one decimated pressure conversion (`260-285`). Each conversion uses 1 µs CNV-high, 1 µs post-CNV wait, then a 16 MHz two-byte receive (`309-319`). The cached repository has no MCP33131 datasheet copy to prove that this falling-edge-to-read delay and 16-clock receive satisfy the selected ADC’s acquisition/conversion timing under the actual source impedance. The firmware README itself calls the 1 µs values pending bench verification. `FLAG_MUX_SETTLE_UNVERIFIED` is correctly carried on every scan, but a successful compile does not establish valid ADC samples.

5. **HIGH — ADC slot timing has no measured proof at the configured 250 µs period.** `PRESCALER=4`, `CC[0]=250` is correctly 16 MHz / 16 = 1 MHz and 4 kHz (`248-258`). The nominal work is 20 × (2 µs settle + CNV/read) plus one pressure slot at 8 µs settle, GPIO writes, `micros()`, EasyDMA setup, polling, and loop overhead. The code records `captureMaxUs` and sets the overrun flag (`280-285`), but there is no measured result in source. Treat 4 kHz as a bench-gated target until health packets show sustained margin and zero ring drops.

## Correct or internally consistent

- The cached Seeed variant maps D8/D9/D10 to P1.13/P1.14/P1.15 and D0..D3 to P0.02/P0.03/P0.28/P0.29. The firmware uses `g_ADigitalPinMap` for SPIM3 and CNV (`297-305`, `309-318`), so the board pin mapping is internally consistent.
- The variant maps `PIN_VBAT=32` to P0.31 and `VBAT_ENABLE=14`; the firmware keeps the enable pin LOW and uses the documented 1.51 MΩ / 510 kΩ ratio in its battery calculation (`13`, `459`, `467`, `196`).
- The ADC word is retained as a 16-bit unsigned transport word (`318`, `383-384`), then converted to signed two’s-complement for dynamic feature accumulation (`355-361`). The G3 host decoder applies the same signed conversion for scan packets (`tools/tactile_v3/protocol.py`).
- Feature packet layout matches the decoder: 20 signed pressure means, 20 unsigned dynamic RMS values, and 20 unsigned peaks (`350-374`; `protocol.py` feature branch). The bridge maps these into 20 contact indices and explicitly normalized `signalNorm`, without claiming PVDF voltage calibration.
- The 50 Hz pressure rate derivation is internally consistent: one pressure conversion every fourth 4 kHz capture, round-robin across 20 channels, gives 80 captures/channel = 50 Hz (`263-279`). Held values are transported between actual conversions.
- DHCX FIFO tag extraction uses `word[0] >> 3` (`141`), which yields the documented five-bit tag field shape. WHO_AM_I is checked against `0x6B` (`121-128`). Freshness is flagged after 100 ms without a changed gyro/accel sample (`401`). Continuous FIFO freshness still needs bench evidence.
- The cached variant confirms D30 is P0.09/NFC1 and D31 is P0.10/NFC2 (`variant.cpp:45-55`). The shutdown code arms active-low sense on P0.09 and disables the analog rail through NFC2/P0.10 (`229-243`), while driving mux/CNV low and ADC MISO high impedance first (`235-240`). This is electrically coherent with the stated wake/analog-enable topology; wake current and UICR behavior remain board tests.

## Remaining protocol/transport issues

- `featureFirstIndex` is assigned but never serialized; the feature packet writes the final window index instead (`350-371`). If the host uses `scanIndex` for timing, it should be defined as window-start or window-end and implemented consistently.
- BLE emits IMU packets at the same queue as feature/raw packets (`168-169`). The eight-slot BLE ring (`42`, `323-329`) can overflow when foreground I2C/USB work stalls service. The firmware counts drops, but the host bridge currently maps only scan/feature frames; add transport health visibility before relying on “connected” as data freshness.
- BLE notification framing itself is compatible with the bridge: the firmware fragments one COBS frame by negotiated MTU (`432-440`), and the bridge accumulates bytes until the COBS zero delimiter. Physical radio throughput, packet loss, and sequence behavior remain unmeasured.

## Action order

1. Separate USB/BLE sequence numbers or carry acquisition sequence unchanged.
2. Replace the unconditional UI deadline with a measured budget and keep OLED/battery work out of capture-critical windows.
3. Bound IMU FIFO reads and expose FIFO overflow/freshness counters.
4. Bench-measure CNV-to-read timing, mux settling, `captureMaxUs`, ring drops, and BLE queue drops on the assembled board.
5. Define and serialize the feature window start index.

## Root follow-up,22October2026

The audit's shared-transport sequence bug is fixed with independent USB/BLE counters. Feature packets now serialize window-start index and timestamp. Foreground admission is bounded by capture-ring capacity; IMU service reads at mosttwo words. ADC timing was checked directly against the existing local DS20005947B (electrical/sources/mcp33131.pdf), which the first audit missed:1µs CNV high exceeds750ns conversion maximum,1µs before read exceeds15ns enable maximum,16MHz is within the clock limits. Setup now adds700ms for the650ms maximum startup calibration. These source checks do not establish actual ISR timing or analog settling. Startup behavior of the pinned Seeed core VBAT_ENABLE remains an explicit review item.
