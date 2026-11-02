# Tactile V4 firmware

Engineering implementation for ESP32-S3-WROOM-1-N8R8:20 dynamic tactile channels at4kHz/channel,20 pressure channels at50Hz/channel, two ISM330DHCX sensors at833Hz, OV5640 VGA JPEG capture, microSD recording, USB data, Wi-Fi data/video and encrypted BLE setup/status/features. V3.3 remains a separate, unchanged target. Hardware bring-up, radio throughput, thermal behavior, optics and six-hour endurance remain measurement gates.

## Build and reproduce

Pinned dependencies:ESP-IDF5.4.2,espressif/esp32-camera2.0.16,espressif/esp_tinyusb1.7.6. Install the ESP32-S3 toolchain with the official IDF tooling, activate its environment, then run:

```sh
idf.py -C firmware/tactile_v4 -B build/tactile-v4 build
python3 tools/tactile_v4/run_native.py --output /tmp/tactile-v4-native
python3 -m pytest tools/tactile_v4/test_protocol.py
```

The build requires both sibling V3 headers `firmware/tactile_v3/tactile_v3_protocol.h` and `button_control.h`. The final artifact manifest records source/dependency hashes and the target build result. Programming a connected device is a separate physical action; these commands compile and test files.

## Processor and bus ownership

| Resource | Owner |
|---|---|
| Core1 GPTIMER interrupt,priority3 |250µs tactile scan; dedicated internal-SRAM128-record ring |
| SPI2/GPSPI2 |Exclusive low-level16MHz ADC read;2-byte register transfers,without per-channel DMA allocation |
| LCD_CAM/GDMA |Camera driver, two PSRAM JPEG buffers |
| SPI3/GDMA |20MHz microSD filesystem |
| I2C0,GPIO4/5,400kHz |Two TCA9535s,camera SCCB,dual ISM330DHCX;one mutex |
| Core0 tasks |Wi-Fi,BLE,USB,SD,camera copy,FIFO reads,packet/features,button/power |

ADC pins:SCK39,MISO40,CNV41. Mux595 pins:clock43,data42,latch38. SD:clock14,MOSI21,MISO47,CS48. Camera:D0..7=11,9,8,10,12,18,17,16;XCLK15,PCLK13,VSYNC6,HREF7. USB19/20;button2;analog enable44;battery ADC1. GPIO35–37 stay available to octal PSRAM;boot strap pins stay outside this allocation.

Foreground packet queue storage resides in PSRAM with internal queue controls;the ISR ring and task stacks remain internal. Wi-Fi/LWIP preferentially use PSRAM. Task creation is checked and allocation failure aborts startup. Actual minimum free heap under combined load remains a bring-up measurement.

Each worst-case scan has144µs explicit analog settling (20×6µs plus one24µs pressure sample),21µs conversion waits and21µs serial clocks,leaving64µs for mux edges,register programming,interrupt/queue overhead and timing guards. That arithmetic is an implementation budget,not measured instruction timing. Each scan records observed elapsed microseconds and flags overruns. Missed GPTIMER slots preserve index gaps rather than pretending an uninterrupted4kHz stream. Physical SPI/mux/ADC timing with simultaneous camera/radio/SD load must pass before acquisition is qualified for use.

## Power and button

The direct active-low GPIO2 button uses the V3 state machine:hold through800ms and release to wake;continue through3s to open a120s pairing window;hold1.5s while running and release to sleep. A tap pauses/resumes tactile capture. Camera recording continues during a tactile pause,which is recorded in health metadata.

USB enumeration,BLE setup and button handling operate before capture qualification. Wi-Fi,SD,IMUs,camera and analog startup wait for a calibrated battery reading≥3.55V,or a valid high-current Type-C advertisement. Capture stops at3.2V;warning is3.4V. A500mA USB enumeration changes only the hardware input-current latch and retains battery hysteresis. BAT_READY is a hardware boot permission,not capture permission. The battery divider is enabled for50ms before eight calibrated samples.

TCA9535 address0x20 controls camera IO/analog/core/interface enables,RESET_N,PWDN,active-low RGB,battery divider,PFM/PWM(reset/startupLOW=PWM;PFM only after loads stop),USB/charger controls and SD_EN on bit15. Address0x21 supplies CC/power/card/IMU status. Full two-byte output transactions commit software state only on success;failed USB latch operations retry. Status bit4 records a control-bus fault. VBUS presence is checked through USB_PG_N before enabling the USB pull-up. Its I2C-mediated latency and actual USB suspend/current behavior require electrical compliance checks.

Camera startup follows the declared independent-rail sequence:IO→20ms→AV→20ms→DV→20ms→interface/XCLK→1ms→PWDNlow→2ms→RESEThigh→26ms→SCCB. Requested XCLK is24MHz;RESET/PWDN live on the expander. Shutdown assertsRESET/PWDN before stopping XCLK,then disables interface,DV,AV,IO in order with20ms rail gaps. Analog shutdown waits for capture/recalibration to stop,drives ADC/mux controls low,then disables its rail. ADC startup includes700ms settling,exactly1024 calibration clocks and700ms completion delay;failed calibration keeps frames explicitly invalid.

RGB:blue blink=pairing;amber=power qualification/calibration or battery warning;red patterned blink=recording/peripheral fault;green=qualified capture;brief periodic green=paused tactile capture. These are active-low expander outputs.

## Data and recording

Wi-Fi uses a WPA2 SoftAP with a per-device random persistent key. Encrypted BLE setup returns SSID,key,address192.168.4.1 and ports7001/7002. New BLE bonds require the physical pairing window;existing bonds reconnect. BLE Secure Connections uses Just Works because the cuff has no numeric display. Physical pairing control limits enrollment;it does not provide a numeric MITM check. USB is a local wired control/data interface.

The cuff serves its bundled viewer at `http://192.168.4.1/` on the private Wi-Fi network. One `/ws` browser session receives50Hz pressure/features, selected raw vibration when requested, dual-IMU FIFO, health, labels and the latest camera frame. Full4kHz scans continue on USB, TCP and SD. Kind9 records browser sensor/JPEG delivery losses once per second in USB/TCP/SD/browser status. The browser has its own64-packet PSRAM queue and independent G3 sequence; delayed previews expose sequence gaps without consuming recording queues. JPEG storage is shared by reference with the browser; one extra leading byte carries the WS type. Each outgoing WS frame has a200ms total send deadline, including partial socket writes, and failed sends close the browser session. The HTTP server serializes its own sends and control frames. Same-origin browser connections and bounded ASCII commands are checked. Radio throughput and browser timing remain physical tests.

TCP7002 and USB emit G3 version2 COBS/CRC16 packets. BLE carries features or selected raw data,health,status and labels with its own sequence counter. `RAW 0`…`RAW 39`,`FEATURES`,and `LABEL TEXT` are accepted over encrypted BLE;USB accepts the same commands terminated by newline. The browser accepts the same commands as complete text frames of at most31bytes. Features continue at50Hz while RAW adds a selected waveform; BLE retains one selected data mode. Labels use1–12 uppercase letters,digits,space,hyphen or slash,persist for the current boot and repeat every second in recordings. Protocol details are in[PROTOCOL.md](PROTOCOL.md).

TCP7001 emits `GV4J` headers followed by JPEG bytes. A camera frame is copied once into bounded PSRAM and shared with separate network and SD queues. A slow receiver has a200ms send deadline and cannot retain a driver camera buffer. Full queues count losses. Continuous acquisition feeds an explicit10fps output schedule. Faster source frames are returned immediately and counted as skipped;selected frames retain actual timestamps. This may produce uneven frame intervals if the sensor rate is not a multiple of10. The pinned VGA/JPEG clock tree is checked by register readback:54MHz SYSCLK and2060HTS. VTS is set to2622 and night-mode frame extension disabled,for9.99756fps nominal. Two startup frames are discarded. Actual frame cadence must be measured. Output pacing does not claim a reduction in sensor power.

SD writes `.g3` and `.gv4j` files with random boot IDs,rotates at1,000,000,000bytes and flushes/fsyncs every second. The switched SD rail enables before card initialization. Shutdown flushes/unmounts the card,drives SCK/MOSI/CS low and disables SD_EN. Mounting never formats a card. Storage failures preserve USB/Wi-Fi operation and increment SD drops. Missing/full/slow cards and JPEG bursts can lose data. A stalled card can exceed the orderly shutdown wait,leaving its final file incomplete. Six-hour lossless recording and card recovery are physical tests still to perform.

## IMU timestamps and identity

Source0=cuff sensor at0x6A,rigid to the camera;source1=dorsal-hand sensor at0x6B. Both exactISM330DHCX chips use833Hz,±4g,±1000dps. These rates and identities are carried in each FIFO payload. Raw chip axes and factory scale are preserved;axis transforms,bias calibration and camera/IMU extrinsics require actual assembly calibration.

Uncompressed FIFO capacity is512 seven-byte wire records,not9kB. The count is ten bits (`DIFF_FIFO[9:0]`),while watermark configuration is nine bits.28-record burst reads use documented0x7E→0x78 FIFO wrap. Timestamp batching is every8ODR slots. Overrun or impossible counts reset the FIFO and discard records until a new timestamp tag. Each batch preserves raw words and a bracketed contemporaneous sensor-clock/MCU-clock anchor with uncertainty. Nominal sensor tick=25µs;long-session clock drift needs anchor-based estimation. Two833Hz streams plus timestamp records occupy about24.8kB/s beforeI2C overhead;controls,anchors and burst/status overhead must fit the shared400kHz bus.

Camera timestamps mark first DMA arrival on `esp_timer`,not exposure start. Tactile channels are sequential within a scan,not simultaneous. Raw IMU axes differ between cuff and hand. These distinctions prevent premature claims of calibrated visual-inertial tracking.

Supply qualification is latched after recording starts: loss of a valid battery measurement, an inadequate remaining source after USB removal, or the battery cutoff requests the same complete camera/SD/analog shutdown as the button. Supply recovery cannot restart loads within that boot. Invalid measurements before first qualification keep acquisition waiting.

## Evidence limits

Native tests execute the same acquisition/features/parser/queue/metadata core compiled into the target,and independently decode its actual output fixtures. They inject deterministic ADC values and modeled durations. The exact HTTP implementation additionally executes against instrumented socket/RTOS boundaries, testing partial writes, deadlines, queue limits, session rejection/reconnect, command limits and shared-image release. These tests do not execute ESP-IDF drivers,prove interrupt latency,validate an OV5640 image,or establish radio/SD throughput. The tiny JPEG fixture tests the framing/CRC,not image encoding. The hardware and six-hour power design remain engineering work even after a successful target compile.

Primary implementation references:[ST DS13012](https://www.st.com/resource/en/datasheet/ism330dhcx.pdf),[ST AN5398](https://www.st.com/resource/en/application_note/an5398-ism330dhcx-alwayson-3d-accelerometer-and-3d-gyroscope-with-digital-output-for-industrial-applications-stmicroelectronics.pdf),[ESP-IDF5.4.2](https://github.com/espressif/esp-idf/tree/v5.4.2),[Espressif camera driver](https://github.com/espressif/esp32-camera).

Shutdown now requires camera/storage-owner acknowledgement before the ordered, checked power sequence. SD unmount faults retain a terminal teardown state; failed power writes remain retryable and cannot acknowledge successful sleep. The pinned camera override in `camera_override/` limits the public frame queue budget to250ms and caps malformed recovery without recursion. The build manifest records the override source identity and confirms that its generated sources are compiled. Permanent peripheral/bus faults still need an independent hardware power-off path; this firmware does not claim that a stalled unit turns off successfully.
