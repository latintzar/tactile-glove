> Earlier camera-free reference revision. This public package retains the V3 sketch and the protocol/button headers required by V4, plus its board/sensing history. The historical V3 build/host-tool records below describe the original development environment; those acquisition tools and prebuilt images are outside this V4 source release. Start with the [current V4 setup](../../docs/setup.md) for the packaged build and host checks.

# Tactile V3.3 firmware

Target: Seeed XIAO nRF52840 Sense, Seeeduino nRF52 core1.1.13. Build:130,688 bytes flash,21,408 bytes static RAM. build/build-evidence.json records the source and artifact hashes. Compilation and simulated tests pass; physical acquisition performance remains to be measured.

## One button

| State | Action | Result |
|---|---|---|
| Off | Hold0.8s, then release | Wake and reconnect bonded host |
| Off | Continue holding to3s | Wake with120s pairing window |
| Running | Tap | Pause/resume collection |
| Running | Hold1.5s, then release | Enter SystemOFF |

The timing state machine uses30ms debounce, emits each hold action once, and handles millis wrap. Fresh power-up opens120s pairing. Wake from SystemOFF uses the TCA9534 interrupt. New BLE peers require pairing mode; established peers reconnect. UART characteristics require encryption without MITM authentication. SystemOFF is an electronic sleep state; external board standby current remains unmeasured.

## Exact GPIO allocation

| Function | GPIO / peripheral |
|---|---|
| SN74AHC595 mux address | D0 SRCLK,D1 SER,D2 RCLK; SPIM2 |
| RGB indicator | Built-in common-anode LED; P0.26 red/P0.30 green/P0.06 blue |
| Spare | D3,D6,D7; SPIM1 unused |
| I2C | D4 SDA,D5 SCL,400kHz; TWIM0 |
| ADC data | D8 SCK,D9 MISO; SPIM3,16MHz |
| ADC convert | D10 CNV |
| Wake interrupt | NFC1/P0.09, active low |
| Analogue power enable | NFC2/P0.10, TPS22919 |
| TCA9534 at0x20 | P0 button; P1–P7 unused outputs LOW |
| ISM330DHCX | I2C0x6B,104Hz accelerometer/gyro |

QA–QD of the shift register select the four4067 banks; QE/QF select the4052 bank. The built-in RGB LED shines through the case's diffused light pipe. Blue breathes during startup/pairing; green is steady when ready and breathes while connected collection is active; amber indicates low battery; two red flashes each second indicate an ADC fault. Fault takes priority, then unqualified supply, pairing and the low-battery warning. Brightness is deliberately bounded. The update rate is50Hz in foreground code. Common-anode PWM is inverted; sleep removes all three PWM pins and sets them HIGH.

Battery acquisition stops below3600mV and resumes at3700mV, with100ms foreground voltage checks and an amber indicator. Real nRF VBUS detection independently qualifies USB-powered operation with an absent battery. Unqualified periods preserve transport/timestamps through zero-filled frames carrying FLAG_POWER_UNQUALIFIED; host software treats those values as invalid. These thresholds are voltage rules, not calibrated percentages. The selected500mAh cell uses its documented100mA standard charging setting: P0.13 sinks LOW, retained throughSystemOFF. Charging temperature and thermal behavior remain physical validation gates. LABEL remains recording metadata on the host.

## Acquisition and format

TIMER4 captures20 vibration channels at4kS/s each. Every fourth capture also reads one pressure channel in round robin, yielding50S/s per pressure channel. A32-slot capture ring separates ISR sampling from transport. TIMER2 is a1MHz32-bit hardware clock extended to64bits; core micros() is unsuitable for this timing. Window flags accumulate across every sample.

MCP33131D-10 uses AVDD1.8V,DVIO3.3V,VREF3.0V and AIN−1.25V. Signed code maps to differential volts as code×3.0/32768. Pressure voltage adds1.25V. The pressure display is a normalized voltage index; force requires calibration. Firmware waits700ms after rail startup, then sends an explicit1024-clock recalibration command and waits another700ms. Failed startup DMA leaves ADC_FAULT output. CNV is high1us, followed by at least125ns output-enable margin before SPI read. Mux settling is6us dynamic and12us pressure, based on the repository circuit model.

Protocol version2 carries the3.0V reference contract. Health extends to42bytes with ADC-reference/midpoint/excitation millivolts at offsets36/38/40. Host decoders retain version1 support for earlier2.5V recordings.

USB carries full raw scans. BLE carries50Hz all-channel features plus IMU/health, or one selected raw channel via RAW0..39. FEATURES restores feature mode; LABEL sets the material text. USB/BLE sequences are independent. Capture/drop counters and source flags remain in host recordings. A full20-channel raw BLE stream is outside this transport contract.

SPI timeouts use persistent DMA storage, bounded STOP/disable, and latch the affected peripheral off until restart. Core Wire polling has a5ms transaction deadline plus1ms bounded abort. A physically held bus returns errors; electrical recovery remains necessary. Real interrupt latency, mux settling, FIFO freshness and throughput are hardware acceptance items. Every scan retains FLAG_MUX_SETTLE_UNVERIFIED until commissioned.

## Build and use

1. Install Arduino CLI and Seeeduino nRF52 core1.1.13.
2. Run tools/tactile_v3/prepare_core.py with that core directory. Its guarded patches put READ_BAT into high impedance at startup and add Wire timeouts. These changes reproduce the supplied firmware.
3. Compile firmware/tactile_v3 for Seeeduino:nrf52:xiaonRF52840Sense.
4. Factory-program build/tactile_v3.hex, or use build/tactile_v3.uf2 with a compatible XIAO bootloader. UF2 family0xADA52840; application base0x27000. Verify build/SHA256SUMS.
5. Install tools/tactile_v3/requirements-preview.txt and run preview_server.py with --ble-address for the actual cuff. Hardware disconnect freezes measurements. Explicit simulation mode labels and preserves synthetic data separately.

The full production sketch executes in the native simulator with41 scenarios passing under ASan/UBSan; see tools/tactile_v3/firmware_sim and hardware/glove-v3/verification/firmware-simulation.md. Regression coverage includes RGB state priority/flash/breathing, button bounce/hold/release/wrap, DMA/Wire injected timeouts, capture ring, packet CRC/framing, timestamp decoding, reconnect cleanup, recording stop/export, quality metadata and control commands. Hardware commissioning must measure timing, every sensor input, overload recovery, supply/reference stability, radio loss, charging, sleep current and mechanical fit.

The fixed waiting/SPI portion of a pressure-bearing scan is198.28125us. Actual ISR overhead plus foreground encoding, USB and SoftDevice time remain unmeasured; the4kHz combined transport deadline is a commissioning gate. Native simulations use synthetic hardware time.
