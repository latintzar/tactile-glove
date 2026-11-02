# RGB cuff firmware adversarial review — 22 October 2026

Scope: the RGB/one-button `tactile_v3.ino`, `button_control.h`, G3 protocol, BLE bridge and local preview server; pinned Seeeduino nRF52 1.1.13 source. Source review establishes the findings below independently of board measurements. Line references identify the reviewed revision; follow-up implementation may move them.

## Confirmed firmware corrections

1. **High — acquisition time uses an unsuitable core clock.** The pinned `cores/nRF5/delay.h:57–60` implements `micros()` as `DWT->CYCCNT / 64` when DWT is enabled, otherwise as `tick2us(xTaskGetTickCount())`. The sketch never enables DWT; its nominal microsecond acquisition duration and timestamps therefore have RTOS tick resolution. Enabling DWT alone also fails: division of a wrapping 32-bit cycle counter makes a 26-bit microsecond counter which wraps every 67.108864 seconds, whereas both `monotonicUs()` and the ISR extend wraps by 2^32. Use an owned 1 MHz hardware timer or correctly extend cycle counts before division. This affects measured `captureMaxUs`, overrun classification, timestamp continuity, freshness and scheduling; it is a desk-level correctness issue, not a request for generic bench timing.

2. **High — battery arithmetic overflows before division.** `serviceUi()` computes `(uint32_t)raw*3600UL*1510UL/(4095UL*510UL)` on a 32-bit ARM target. For the 3.7 V fixture, raw1421 yields 1642 mV after overflow instead of 3698 mV. Promote the numerator to uint64_t before multiplication. `test_battery.py` currently uses Python integers and cannot catch this target-width error.

3. **Medium — window flags discard faults from earlier scans.** `queueBleSelection()` and `queueBleFeatures()` write the flags supplied with the last scan of a 40/80-scan window. A fault or acquisition gap on an earlier scan vanishes from the packet. Accumulate flags with bitwise OR and reset them with each window; preserve flags while resetting a window after a capture gap. The bridge previously omitted frame flags; this review now forwards them and preserves flags/sequence/device time/index/health in recording exports.

4. **Medium — EasyDMA failure paths return before STOPPED.** `rgbSend()`, `selectMux()` and `adcRead()` issue `TASKS_STOP` on timeout and immediately return; their DMA sources/destination may be stack-local (`command`, `address`, `rx`). A timeout path must wait for STOPPED or otherwise disable the peripheral and use storage whose lifetime outlives the abort. Success paths wait for END and have suitable stack lifetimes. This is a bounded failure-path defect, not evidence of ordinary transfers failing.

## Host corrections implemented during this review

- Fixed the scan IMU high-word offset in `protocol.py`: firmware writes low at10 and high at12; decoder previously read both at10. Added a nonzero high/low word fixture (0x12345678).
- Split a BLE connection session from its retry loop. The bridge now reconnects after disconnect, subscription failure or command-write failure, until cancelled.
- Connected state is now published only after notification subscription succeeds. Cleanup clears state, partial framing, previous health and queued commands even when subscription/notification cleanup fails. Commands from a previous connection cannot replay after reconnect.
- Command writer exceptions now reach the connection lifecycle rather than silently killing the writer while the bridge continues claiming it can accept commands.
- Added failure-injection tests for subscription failure, write failure, notification cleanup failure, reconnect and stale-command cleanup.

Validation: `TMPDIR=/tmp/glove-eda-runtime PYTHONPATH=tools/tactile_v3 python3 -m pytest -q -s -p no:cacheprovider tools/tactile_v3/test_protocol.py tools/tactile_v3/test_bridge.py tools/tactile_v3/test_host_control.py tools/tactile_v3/test_battery.py` → 9 passed. Battery fixture script also passed; its target-width limitation is described above.

## Additional preview defect reported to the owner

The original record-button handler sets `recording=false` before calling `stopRecording()`, whose first statement returns when recording is false. A normal explicit stop therefore skips the JSON download and UI reset. Fixed during this review: start sets recording true; stop calls `stopRecording()` while recording remains true. The Node regression executes the actual shipped handlers and verifies one JSON download, UI reset, restart, and disconnect stop.

## Ownership, interrupt and protocol checks

- Wire uses TWIM0; RGB uses SPIM1; mux uses SPIM2; ADC uses SPIM3. The physical register ownership is now disjoint while Wire1 remains unused.
- `Wire.begin()` sets NVIC priority3, but this pinned driver's master path enables no TWIM interrupt mask. Reads/writes poll in foreground, so TIMER4 priority6 can preempt that work. The misleading priority number alone does not establish an I2C ISR blocking capture.
- SoftDevice priority0/1/4 can preempt TIMER4 priority6; actual resulting capture duration remains a physical performance property. The clock defect above must be fixed before those reported durations are meaningful.
- The pinned Wire driver has unbounded event polling on bus faults. A stuck bus can strand the foreground while capture fills its ring; the existing `uiDeadline()` admission check does not bound a stuck transaction. This merits bounded I2C recovery in the product handoff.
- G3 frame sizes fit the current transport buffers: scan116 bytes in USB128, feature150 bytes in BLE192, selected raw114 bytes in BLE192. The protocol helper's generic “256 bytes” comment is more conservative than these actual call sizes.
- Button timing logic handles the tested bounce/tap/hold/release and millis wrap cases. The setup path begins qualification before its 700 ms ADC startup wait; this closes the previously reported wait-induced false hold.
- The current firmware README still described the superseded GPIO mux, two buttons and SSD1306 display when inspected; its pin/display contract must follow the released RGB/shift-register source.

## Release conclusion

The host lifecycle, scan timestamp decoder and explicit recording stop are fixed and regression-tested. Follow-up source review confirms the owned timer clock, uint64 battery numerator, and OR-accumulated packet flags are implemented by the owning agent. DMA-abort lifetime and bounded I2C polling are now implemented and covered by injected-fault tests; see the robustness follow-up below. Board performance remains a separate acceptance stage.

## Clock follow-up reviewed

The owning agent replaced core `micros()` with TIMER2 running at 1 MHz, a wrap epoch updated by the capture ISR even while paused/full, and a foreground seqlock. Separate capture registers serve ISR epoch updates and foreground reads. Unsigned 32-bit subtraction preserves short durations across timer wrap. The pinned core reads TIMER2 CC0 into its bootloader-version variable in `init()`, before sketch setup; the new ownership begins after that read. This closes finding1 at source level. The hardware timing acceptance stage remains unchanged.

Additional host validation: `node tools/tactile_v3/test_preview_recording.cjs` passed; `node --check hardware/glove-v3/software-preview/preview.js` passed. Standalone protocol, bridge and host-control script entry points were also exercised.

## Robustness follow-up implemented

- `dma_abort.h` issues STOP, waits for STOPPED with a 100 µs timer deadline plus a 4096-poll fallback, disables the SPIM peripheral, and clears DMA pointers/counts. RGB, mux and ADC DMA storage is now static and aligned, including all former stack sources/destinations. A transfer timeout latches that SPI peripheral disabled until device restart. Subsequent calls fail immediately; a failed mux selection skips its ADC conversion. Existing display/ADC fault reporting remains in effect.
- `prepare_core.py` reproducibly installs the owned `core_patches/cuff_wire_timeout.h` into the pinned core and replaces all eight master-mode Wire wait loops. A transaction shares a 5 ms deadline across start/data/stop-or-suspend phases. Timeout requests STOP with a separate 1 ms deadline, disables TWIM, clears DMA/event state, and returns Arduino error4 or zero received bytes. The next transaction re-enables the controller. A finite million-poll ceiling also terminates if scheduler time stops advancing. Preparation validates both source transformations before writing and is idempotent.
- Bounds are polling deadlines, not a guarantee against arbitrarily long higher-priority interrupt execution. The patch does not pulse SCL/SDA or power-cycle a peripheral: a physically held bus remains a repeated reported error. Source tests cannot demonstrate actual electrical recovery. SPI faults intentionally require restart rather than resuming from uncertain hardware state.

Validation of the final robustness source:

- Latest full Seeeduino1.1.13 compile: **131760 bytes flash; 37620 bytes static RAM**. Output `/tmp/glove-eda-runtime/tactile-build/tactile_v3.ino.hex` and matching ELF. Compile exit0; the local Arduino library-index cache emitted its existing EOF initialization warning, which did not prevent compilation.
- Host-compiled `test_peripheral_timeouts.cpp`: missing event, NACK, STOP failure/success, frozen scheduler clock, millis wrap, SPI disable and next I2C prepare all passed.
- Python core-patch guards/idempotence plus protocol/bridge/host control: **12 passed**.
- Button FSM, SPSC capture ring/pressure round robin, and preview recording regression passed.

The compile used a temporary runtime `python` shim pointing to the installed Python3 because the pinned platform recipe invokes `python`. No board was flashed during this work.
