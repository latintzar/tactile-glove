> Historical audit of the pre-shutdown-fix firmware. See README.md here for the current implementation. The GPIO3/TCA9539 circuit and restart sketch remain unapplied.

# V4 safe-shutdown correction design (isolated)

Date: 2026-10-23
Status: proposal only. Nothing in the canonical firmware, PCB, or power netlist was changed.

## Decision under review

Replace only `U_IO0` with TI `TCA9539PWR`. It is the same PW-24 package footprint as the present `TCA9535PWR`; P00..P17 keep the existing output assignments. The TCA9539 reset pin is pin 3. Route it to a new direct MCU net `MCU_IO0_RESET_N` on currently-NC ESP32-S3 GPIO3, with a 10 kOhm pulldown to GND. Keep `U_IO1` as TCA9535PWR at 0x21. For TCA9539, A1 pin 2 and A0 pin 21 remain GND, giving address 0x74. The proposed reset wire is the only PCB change described here; it is awaiting PCB-owner approval.

The TCA9539 datasheet specifies RESET as active-low and ports as inputs after reset/power-up. The pulldown therefore holds IO0 in its input state during MCU boot and after an I2C/control failure. GPIO3 is absent from the pinned ESP32-S3 SD/boot strapping list (the IDF list names GPIO0, GPIO45 and GPIO46). The pinned IDF also documents GPIO3 as the optional JTAG-selection strap only when the irreversible `STRAP_JTAG_SEL` eFuse is burned; with the default USB_SERIAL_JTAG path it is an ordinary GPIO. Record the eFuse state and run the exact module boot smoke test before release. Source: <https://www.ti.com/lit/ds/symlink/tca9539.pdf>; pinned IDF evidence is `sd_pullup_requirements.rst`.

## IO0 failoff audit

Resetting the expander only makes its pins inputs. A safe power-off state depends on an external default for every output. The canonical whole-board component list has explicit defaults for all sixteen outputs. The earlier power-only view omitted the subsystem resistors; this corrected audit uses `hardware/glove-v4/electrical/components.json` (561 components):

| IO0 port | net | current default evidence | failoff result after TCA9539 reset |
|---|---|---|---|
| P00 | CAM_IO_EN | R_CAM_IO_EN, 100 kOhm to GND | low; TPS7A2018 enable off |
| P01 | CAM_AV_EN | R_CAM_AV_EN, 100 kOhm to GND | low; TPS7A2028 enable off |
| P02 | CAM_DV_EN | R_CAM_DV_EN, 100 kOhm to GND | low; TPS7A2015 enable off |
| P03 | CAM_IF_EN | R_CAM_IF, 100 kOhm to GND | low; camera interface disable path asserted |
| P04 | MCU_CAM_RESET_N | R_CAM_MCU_RESET, 100 kOhm to GND | low, sensor held reset |
| P05 | MCU_CAM_PWDN | R_CAM_MCU_PWDN, 47 kOhm to 3V3_SYS | high, sensor power-down |
| P06 | LED_R_N | 47 kOhm to 3V3_SYS | high, LED off (active-low) |
| P07 | LED_G_N | 47 kOhm to 3V3_SYS | high, LED off (active-low) |
| P10 | LED_B_N | 47 kOhm to 3V3_SYS | high, LED off (active-low) |
| P11 | BAT_DIV_EN | 100 kOhm to GND | low, divider off |
| P12 | REG_PFM | 100 kOhm to GND | low; confirm TPS63070 low-state meaning |
| P13 | USB_CONFIG_SET | 100 kOhm to GND | low |
| P14 | USB_CONFIG_CLR_N | 100 kOhm to GND | low, clear asserted |
| P15 | USB_SUSPEND | 100 kOhm to GND | low; confirm USB switch state |
| P16 | CHG_DISABLE | 100 kOhm to GND | low; charger-disable polarity must remain documented |
| P17 | SD_EN | R_SD_EN, 100 kOhm to GND | low; TPS22919 enable off |

This table is a release gate: the timeout/reset path may rely on these defaults only after the exact resistor population and downstream enable polarity are checked in PCB CAD and on first article. The table is derived from the canonical 561-component list, not from a physical board measurement.

## Bounded shutdown routine

The current code waits up to three seconds for `cameraStopped` and `sdStopped`, then calls `holdSdPinsLow()` and removes camera/SD rails even if either worker is still alive. `esp_camera_fb_get()` is called without an application timeout. In the pinned HAL, `cam_take()` can wait on the frame queue and `cam_deinit()` stops DMA, deletes the camera task/queues, then frees DMA buffers. Calling `esp_camera_deinit()` from a second task while the capture task may still be in `esp_camera_fb_get()` is unsafe.

The proposed routine is an ownership protocol:

1. Set `sleeping`, stop the acquisition timer, and wait for the ADC critical section with a bounded deadline.
2. Set camera and storage stop requests and close network sockets. The camera task owns `esp_camera_fb_return()` and `esp_camera_deinit()`; it must acknowledge only after the final frame is returned, `esp_camera_deinit()` has returned, and the XCLK LEDC output is stopped. The storage task owns `fclose`, unmount, `spi_bus_free`, `holdSdPinsLow`, and SD_EN off, and acknowledges only after those operations complete.
3. Wait for both acknowledgements with a fixed deadline. `spi_bus_free` is called only by the storage owner after unmount and after no SD device remains attached, as required by the pinned IDF SPI documentation.
4. Only after both acknowledgements, under `busMutex`, stop the IMU, assert camera reset/PWDN, stop XCLK, isolate camera I/O, remove camera rails in the documented order, then remove SD power. Check every IO0 write result.
5. If the deadline expires, do not power down a rail or assert GPIO3 from the live application while its worker may still own DMA or SPI. Call `esp_restart()` directly, with no custom shutdown handler that touches camera/SD. The pinned ESP-IDF invokes registered handlers, suspends scheduling, disables interrupts, resets selected DMA/timer/SPI modules, then resets both CPUs. Its source does not reset GPIO configuration, and GPIO3 may remain an output-high across this software reset; the external pulldown cannot be treated as an automatic reset. SPI3 is also not named in the reset mask, so keep SD power applied through reset. At the first app entry after reset, before releasing IO0 RESET: hold SD pins low, disable SPI3, stop XCLK/put camera GPIOs in input, disconnect GPIO3's old matrix function, explicitly drive GPIO3 low, disable its internal pullup, enable its pulldown, and only then remove rails through TCA9539 RESET. This sequence avoids deleting a live task and avoids an application-side rail cut while DMA is active. Verify reset-line, SPI3 pins, and rails with an oscilloscope capture.

The routine must never use `vTaskDelete(cameraTask)` from `sleepNow()`, call `spi_bus_free()` from `sleepNow()`, or call `holdSdPinsLow()` while the storage worker is alive. These are worker-owner operations. The current three-second loops are deadlines, but their fallback actions violate that ownership rule.

## Proposed firmware shape (not applied)

`proposed-patch.design.diff` is a review sketch. It adds the GPIO3 reset net, an explicit post-restart GPIO quiesce sequence, owner stop acknowledgements, and a timeout branch that keeps rails applied through `esp_restart()` before first-app GPIO3 reset. It intentionally does not claim to compile: the camera/storage task handles and acknowledgement objects must be threaded through the existing task creation code after the PCB net is approved.

## Evidence and unresolved release items

* Camera component contract: the pinned project declares `espressif/esp32-camera ==2.0.16`, but its wrapper implementation is absent from the local SDK snapshot. The locally pinned HAL is therefore the only inspected implementation.
* Camera public API: `esp_camera_deinit()` is the available public stop API. The pinned HAL implementation calls `cam_stop()` before deleting the camera task and freeing DMA buffers. The pinned public header has no timeout argument for `esp_camera_fb_get()`. The local HAL `cam_take(timeout)` has a queue timeout, but on ESP32-S3 its GDMA recovery path can perform a second wait with the same timeout; expose that bounded owner-call only after checking the exact linked camera component.
* SD API: `esp_vfs_fat_sdcard_unmount()` followed by `spi_bus_free()` is the available owner sequence. The existing storage worker already owns this sequence.
* GPIO3: not a normal ESP32-S3 power/SD strap in the pinned IDF list, but it is the optional JTAG-selection strap when `STRAP_JTAG_SEL` is burned. Record that eFuse state, validate the exact ESP32-S3-WROOM module boot behavior with the 10 kOhm pulldown and confirm GPIO3 drive-high timing.
* TCA9539 reset: verify the selected library/driver treats 0x74 as IO0 after the part swap and that the PW-24 land pattern is pin-compatible in the board CAD.
* Failoff: canonical resistors now cover all seven camera/SD control nets; verify their populated values, downstream polarity, and reset-line/rail timing on first article. Also confirm the active polarity of REG_PFM, USB_SUSPEND, CHG_DISABLE and the downstream USB gates.
* Timeout recovery: implement the boot-time quiesce sequence (SD pins low, SPI3 disabled, XCLK/camera GPIOs quiet, GPIO3 matrix disconnected and explicitly driven low with internal pullup disabled) after `esp_restart()`. Do not release a production image while a timeout path can remove a rail with an active worker or while SPI3 reset/disable timing is unmeasured.

## Source hashes

See `source-hashes.txt` and `io0-failoff-audit.json`. The hashes pin the current review inputs; they do not turn this proposal into a firmware or hardware validation.
