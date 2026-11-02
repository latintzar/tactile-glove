# V4 factory flashing, test and phone setup

The supplier delivers the populated, programmed and tested cuff with camera, card, protected battery, hand IMU and labeled harnesses fitted. The wearer fits the prepared tactile laminate and plugs the keyed branches. This procedure covers the engineering first article; fabrication release and measured six-hour endurance remain separate gates.

## Exact assembly

| Item | Selection and inspection |
|---|---|
| Controller | ESP32-S3-WROOM-1-N8R8: 8 MB flash, 8 MB octal PSRAM |
| Camera | CamThink `73.002.000035`, OV5640 120° field of view, 8 cm preset fixed focus (shop variation506); verify supplied tail drawing; [source/quote](../procurement/camera-sourcing.md) |
| Camera connector | Hirose FH12-24S-0.5SH(55), 24 contacts, 0.5 mm pitch, bottom contact, 0.3 mm tail; verify pin 1/contact side against [camera-interface.json](../interfaces/camera-interface.json) before insertion |
| Camera supplies | DOVDD 1.8 V, AVDD 2.8 V, external DVDD 1.5 V; exact SN74AXC8T245PWR translators |
| Battery | Jauch 250480, LI18650JLS HB 1S2P+PCM+FUSE+2 WIRES 70MM; 6.5 Ah minimum, 3.6 V nominal, 4.2 V charge, PCM and 7 A fuse |
| Battery harness | Direct Micro-Fit harness: crimp the unmodified Jauch AWG22 red/black leads into Molex `43030-0007` contacts and insert them into `43025-0200`, mating PCB header `43045-0200` (pin 1 +/red, pin 2 −/black). Install the Littelfuse `045102.5MRL` 2.5 A fast fuse in the positive entry path before board branches. Perform continuity, isolation and crimp-pull checks on an unpowered dummy or disconnected board-side harness; use a voltmeter and controlled load/charge simulation for the connected pack. Record polarity, voltage drop and final 70 ±5 mm lead route. Fit the separate Semitec 103AT-2 thermistor under insulation |
| Storage | Kingston SDCIT2/32GB, microSDHC, FAT32; Hirose DM3AT-SF-PEJM5; firmware SPI 20 MHz |
| IMUs | ISM330DHCXTR: source 0/cuff 0x6A rigid to camera; source 1/hand 0x6B on the remote tile; both 833 Hz, ±4 g, ±1000 dps |

The pack is nominally 69×38×20 mm, 100 g; apply its drawing tolerances and final enclosure clearance report. The Micro-Fit interface uses the direct or specified 35 mm-per-lead extension variant after the exact reach check in the battery-harness procedure; the sealed pack stays intact. The two-wire pack supplies no accessible NTC lead. Designed charging is 1.205 A nominal, 1.28 A documented maximum, within the pack's 2 A limit; temperature qualification is 10–45 °C. See [current energy/power evidence](../verification/energy-budget.md) and [pack source/drawing](../procurement/battery-candidate-jauch250480.json).

## Programming

Build your own target image using the [pinned ESP-IDF setup](../../../docs/setup.md#esp32-s3-target-build). The [artifact directory](../../../firmware/tactile_v4/artifacts/) preserves historical compile hashes/configuration and flash descriptions. Historical target/bootloader/partition images are retained privately pending complete binary-linked SDK notices; the public start path is source build and host verification.

After routing/manufacturing acceptance and assembly, deliberately select your actual device and use the SDK-generated images/flash arguments for that exact hardware build. Keep your generated source/binary hashes with the completed acceptance record.

## Electrical and recording acceptance

Enter actual measurements and traces in [factory-record-template.json](factory-record-template.json). Software test results establish expected behavior; measured fields stay empty until the supplier performs them.

| Check | Expected behavior and evidence |
|---|---|
| Power/battery | Main rail 3.416 V nominal. Capture starts/resumes at 3.55 V, warning 3.4 V, orderly stop 3.2 V under load. BAT_READY permits MCU/USB recovery; capture qualification is separate. A 500 mA USB enumeration retains battery hysteresis; valid high-current Type-C can qualify capture |
| Charging | Measure 4.2 V regulation, charge-current bounds and pack-temperature cutoffs; retain polarity, thermistor-attachment and thermal records |
| Camera startup | IO →  20 ms → AV → 20 ms → DV → 20 ms → interface/XCLK → 1 ms → PWDN low → 2 ms → RESET high → 26 ms → SCCB. Scope all three rails, RESET/PWDN and requested 24 MHz XCLK |
| Camera shutdown | RESET low/PWDN high precede XCLK off/interface off; DV off → 20 ms → AV off → 20 ms → IO off |
| Camera image | 640×480 JPEG quality 12, nominal 9.99756 fps, actual first-DMA timestamps. Inspect scale/checker targets at 5, 8, 10, 20 cm and actual fingertips; record focus, usable field, cadence, CRC rejects and sequence gaps |
| IMUs | Kind 6 carries both IDs/addresses, 833 Hz and scales. Record stationary bias and distinct raw axes. Retain FIFO-overrun recovery/timestamp metadata; assembly calibration and rigid camera extrinsics are separate measurements |
| Tactile | 20 dynamic×4 kHz and 20 pressure×50 Hz. Verify all channel wiring with known stimuli. Scope worst-case mux transitions and the 250 µs scan with camera/Wi-Fi/BLE/SD active; retain elapsed time, ADC faults, ring drops and IMU overruns |
| Card/files | Confirm kind 7 SD-mounted flag; verify `.g3`/`.gv4j` CRC, timestamps, labels, 1 GB rotation and shutdown flush. Characterize full/missing/stalled-card behavior |
| Preview | Kind 9 reports browser sensor/JPEG losses. Disconnect/reconnect the viewer and compare preview loss with independent SD continuity |
| Sleep | Capture stops before analog-off; ADC/mux controls go low. SD flush/unmount precedes SCK/MOSI/CS low and rail-off. PFM follows camera/SD/analog shutdown. Measure standby current |

The current firmware retains the mux-settling-unverified flag. Record physical evidence before a later engineering change qualifies that flag. Pressure is an electrical contact level until calibrated to force; raw camera/IMU timing and axes remain explicit until assembly calibration.

## Button and light

From sleep, hold 800 ms and release to wake; continuing through 3 s opens the 120 s pairing window. While running, hold 1.5 s and release to sleep. For pairing from a running cuff, sleep first and then wake with the 3 s hold. A tap pauses/resumes tactile capture while camera recording continues; health metadata records that pause.

Blue blink means pairing; amber means qualification/calibration or battery warning; green means capture; periodic brief green means tactile paused; red patterned blink means peripheral/recording fault. Test the assembled button cap using the other gloved hand, recording deliberate press/release and accidental-contact resistance.

## Phone handoff

1. In an authorized HTTPS Web Bluetooth setup page on a supported browser, open the physical pairing window and connect to `Artisan Tactile V4`. Read encrypted setup characteristic `a4c40004-a88b-4d5d-9b67-e81c2a180de0`: newline-separated SSID, password, address and TCP ports.
2. Produce the cuff's private Wi-Fi label/QR from those actual credentials. SSID is `Artisan-` plus device suffix; the 20-character WPA2 key persists in NVS. Keep credentials in the supplier's private device record, outside this repository.
3. The wearer scans the Wi-Fi QR or joins that network, then opens **http://192.168.4.1/**. Supply this address as a second link/QR. The cuff serves its viewer assets locally.
4. Confirm camera, pressure map, selected waveform, IMU/battery status and recording/drop counters. `Mark take` writes a label; powered capture already records continuously to the installed card.

The Wi-Fi QR route supports ordinary phone browsers, including phones without Web Bluetooth. The HTTPS setup route uses a supported browser; the local HTTP viewer operates after joining Wi-Fi. One Wi-Fi station and one live viewer session are supported.

## Six-hour run and delivery

The battery provides a 6.019 h conservative scenario calculation. Actual acceptance requires at least six hours of complete recordings at the production operating point, from full charge through the 3.2 V stop, using the supplied camera, card, firmware and enclosure. Retain current, rail transients, pack/skin-facing temperatures, cadence, quality/drop counters and file integrity.

The exact scan-only floor is116 bytes ×4000/s =464,000 bytes/s:10.0224 GB per six hours and40.0896 GB per24 hours. A32 GB card therefore cannot retain a full24-hour day even before camera or IMU data. [The capacity record](storage-budget.json) derives packet size from4000 actual firmware-produced scans. Verified offload and available-space checks are part of the daily recording workflow.

Card capacity also requires measurement. Full-rate scans, dual IMUs and features use approximately 11 GB over six hours before video. With 10% free-space reserve, a 32 GB card leaves approximately 82 kB/JPEG at 10 fps. Calculate the actual margin from the card's free bytes and measured file growth; JPEG scene complexity determines the real consumption.

Ship the serial-linked flash log, checksums, part/lot photographs, scope/thermal/cadence measurements, acceptance recordings and completed record. Deliver the Wi-Fi label privately. The supplier completes electronics, programming and integration; the wearer receives the prepared laminate kit and keyed harnesses.
