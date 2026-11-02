# Shutdown fault verification

The pre-fix firmware waited three seconds for camera/storage, then changed SD pins and removed power even if a worker still owned DMA/SPI. An I2C write failure could also be followed by deep sleep with loads still powered. The battery-source gate had a separate gap: lost ADC evidence could disable tactile capture without requesting camera/storage shutdown.

## Implemented correction

`PowerGate` latches any loss of previously qualified supply evidence and requests complete shutdown. Initial invalid readings keep capture waiting. Recovery requires a new boot.

`ShutdownSequence` is executed only after both camera and storage owners acknowledge. It checks each IMU/reset/clock/interface/rail operation, retaining the same phase after failure. Deep sleep follows only successful completion. SD teardown remains in its owning task: close files, unmount, release SPI, isolate pins, confirm SD power off, then acknowledge. A failed non-idempotent unmount latches a teardown fault; a failed power write is retried without a false acknowledgement. The camera owner asserts sensor RESET/PWDN before deinitialization stops XCLK and acknowledges only successful teardown. Camera completion precedes the request to drain/close SD so the last frame can reach storage.

The native fault matrix blocks progress with either owner active and injects three consecutive failures at each of seven ordered phases before recovery. It verifies that later operations never run early and completion is idempotent. These tests execute the exact shared shutdown sequence; they do not emulate the IDF peripheral drivers or a physical stuck bus.

## Camera driver

The pinned2.0.16 wrapper used a four-second queue timeout; its ESP32-S3 fallback could wait twice. Invalid JPEG handling recursed, allowing growing stack depth while a tick remained unchanged. The integrated hash-checked override uses one250ms total queue budget, one GDMA recovery and at most three malformed frames. Nine ASan/UBSan cases execute its actual cam_take body; the complete ESP32-S3 target build and compile-command/source-hash checks confirm that the generated override is linked. Scheduling latency, image processing time and a hardware/peripheral deadlock remain outside that queue-time bound.

## Remaining hardware fault path

A permanently stalled peripheral owner, failed unmount or unusable control bus can leave rails powered while shutdown waits. The software now preserves ownership and reports no successful off state in that condition. An independent reset/power-off path, watchdog/reset sequencing and thermal intervention still require integration. The separate TCA9539/GPIO3 proposal is unapplied; its exact boot pin timing and charge-disable defaults need resolution. The existing charge NTC does not measure battery temperature during discharge.

The historical audit and source evidence are preserved alongside this file. They explain the original defect and reset proposal; the current firmware and build manifest own implementation status. No manufactured unit was programmed or measured.
