#include <Arduino.h>
#include <Wire.h>
#include <bluefruit.h>
#include <Adafruit_TinyUSB.h>
#include "nrf_gpio.h"
#include "nrf_soc.h"
#include "tactile_v3_protocol.h"
#include "channel_map.h"
#include "button_control.h"
#include "dma_abort.h"
#include "indicator.h"
#include <HardwarePWM.h>

// Hardware ownership: Wire/TWIM0, mux/SPIM2, ADC/SPIM3, onboard RGB/PWM0.
// UI service keeps button/indicator work separate from the capture ISR.
constexpr uint8_t BUTTON_ADDR = 0x20;
constexpr uint8_t TCA_CONFIG = 0x03, TCA_POLARITY = 0x02, TCA_INPUT = 0x00, TCA_OUTPUT = 0x01;
constexpr uint8_t BAT_ENABLE_PIN = 14, BAT_ADC_PIN = 32;
constexpr uint8_t WAKE_IRQ_PIN = PIN_NFC1;   // physical NFC1, nRF P0.09, TCA9534 INT
constexpr uint8_t ANALOG_EN_PIN = PIN_NFC2;  // physical NFC2, nRF P0.10, TPS22919 ON

using namespace TactileV3;

// XIAO nRF52840 Sense pins. I2C is D4/D5; ADC SPI is read-only.
constexpr uint8_t I2C_SDA = D4, I2C_SCL = D5;
constexpr uint8_t MUX_SRCLK = D0, MUX_SER = D1, MUX_RCLK = D2;
constexpr uint8_t ADC_SCK = D8, ADC_MISO = D9, ADC_CNV = D10;
// Fixed XIAO physical pins avoid runtime GPIO-map/port branches in the ISR.
constexpr uint32_t MUX_LATCH_GPIO=28, ADC_CNV_GPIO=47;
constexpr uint8_t IMU_ADDR = 0x6B;
constexpr uint8_t IMU_WHO_AM_I = 0x0F;
constexpr uint8_t IMU_TIMESTAMP0 = 0x40, IMU_FIFO_DATA_OUT_TAG = 0x78;
constexpr uint8_t IMU_FIFO_STATUS1 = 0x3A, IMU_FIFO_STATUS2 = 0x3B;
constexpr uint8_t IMU_FIFO_CTRL1 = 0x07, IMU_FIFO_CTRL2 = 0x08, IMU_FIFO_CTRL3 = 0x09;
constexpr uint8_t IMU_FIFO_CTRL4 = 0x0A;
constexpr uint8_t IMU_CTRL1_XL = 0x10, IMU_CTRL2_G = 0x11, IMU_CTRL10_C = 0x19;

// 20 dynamic samples every 250 us; one pressure sample every fourth frame.
// ADC serial limits are source-checked; complete ISR timing remains bench-gated.
constexpr uint16_t DYNAMIC_RATE_HZ = 4000;
constexpr uint16_t PRESSURE_RATE_HZ = 50; // per channel; 1 kS/s aggregate
constexpr uint32_t SLOT_BUDGET_US = 1000000UL / (DYNAMIC_RATE_HZ * 20UL);
constexpr uint32_t PRESSURE_SETTLE_US = 12;
constexpr uint32_t DYNAMIC_SETTLE_US = 6;
constexpr uint32_t ADC_CNV_HIGH_US = 1;
static inline void adcOutputEnableWait(){
  // Eight CPU NOPs give at least125ns at64MHz; ADC tEN is at most15ns.
  __NOP();__NOP();__NOP();__NOP();__NOP();__NOP();__NOP();__NOP();
}
constexpr uint16_t FRAME_BYTES = 94;
constexpr uint8_t BLE_QUEUE_SLOTS = 8;
constexpr uint16_t BLE_FRAME_BYTES = 192;
constexpr uint8_t USB_QUEUE_SLOTS = 8;
constexpr uint16_t RAW_BATCH_SAMPLES = 40;
constexpr uint16_t FEATURE_WINDOW_SAMPLES = 80;
static uint64_t nextImuReadUs = 0;
struct UsbFrame { uint16_t bytes, offset; uint8_t data[128]; };
static UsbFrame usbQueue[USB_QUEUE_SLOTS];
static uint8_t usbHead = 0, usbTail = 0;
struct BleFrame { uint32_t session; uint16_t bytes, offset; uint8_t data[BLE_FRAME_BYTES]; };
static BleFrame bleQueue[BLE_QUEUE_SLOTS];
static uint8_t bleHead = 0, bleTail = 0;
static int8_t bleRawChannel = -1;
static uint32_t bleDrops = 0;
static volatile uint16_t activeConnection = BLE_CONN_HANDLE_INVALID;
static volatile uint32_t bleSessionEpoch=0;
static uint32_t appliedBleSessionEpoch=0;
static bool bleDelimiterPending=false;
static bool bleEnabled = false;
static uint32_t usbPacketSequence = 0, blePacketSequence = 0;
static uint32_t txDrops = 0, usbDrops = 0;
static uint64_t nextScanUs = 0;
static uint16_t rawBatch[RAW_BATCH_SAMPLES];
static uint16_t rawBatchCount = 0, rawBatchFlags=0, featureWindowFlags=0;
static uint32_t rawBatchFirstIndex = 0;
static uint64_t rawBatchFirstStamp = 0;
static int64_t featurePressureSum[20] = {}, featureDynamicSum[20] = {};
static uint16_t featurePressureCount[20] = {};
static bool pressureSampleThisScan = false;
static uint8_t pressureSampleChannel = 0;
static uint64_t featureDynamicSq[20] = {};
static uint16_t featureDynamicPeak[20] = {};
static uint16_t featureCount = 0;
static uint32_t featureFirstIndex = 0;
static uint64_t featureFirstStamp = 0;
static bool imuReady = false;
static uint32_t imuTimestamp = 0;
static bool queueBle(uint8_t kind, uint64_t stamp, const uint8_t *payload, uint16_t length);
static int16_t imuGyro[3] = {}, imuAccel[3] = {};
static uint16_t imuFifoWords = 0;
static volatile bool acquisitionPaused = false;
static CuffButton::Control powerButton;
static bool pairingMode=false, lowBattery=false;
static uint32_t pairingUntil=0;
static char materialLabel[13]="TEXTURE";
static uint16_t batteryMv = 0;
constexpr uint16_t BATTERY_ACQUIRE_MIN_MV=3600, BATTERY_RESUME_MV=3700;
static volatile bool powerQualified=false;
static bool adcCalibrated=false;
static bool batteryQualified=true, usbPowerPresent=false;
static uint64_t lastGyroUpdateUs = 0, lastAccelUpdateUs = 0;
static uint32_t nextUiMs = 0, nextBatteryMs = 0;
static bool shutdownRequested = false;
struct Capture { uint64_t stamp; uint32_t sequence; uint8_t pressureValid, pressureChannel; uint16_t flags; uint16_t pressure[20], dynamic[20]; };
constexpr uint8_t CAPTURE_SLOTS = 32;
static Capture captureRing[CAPTURE_SLOTS];
static volatile uint8_t captureHead = 0, captureTail = 0;
static volatile uint32_t captureDrops = 0;
static volatile uint8_t isrPressureRoundRobin = 0;
static volatile uint32_t isrCaptureSequence = 0;
static volatile uint32_t captureMaxUs = 0;
static volatile uint32_t captureAdcErrors = 0;
static volatile uint32_t captureLateEvents = 0;

BLEService tactileService("6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
BLECharacteristic tactileTx("6E400003-B5A3-F393-E0A9-E50E24DCCA9E");
BLECharacteristic tactileRx("6E400002-B5A3-F393-E0A9-E50E24DCCA9E");

// TIMER2 is a dedicated1MHz32-bit free-running clock. The pinned core's
// micros() is RTOS-resolution unless DWT is enabled, and DWT wraps at67s.
static volatile uint32_t clockEpoch=0, clockLast=0, clockVersion=0;
static void clockBegin(){
  NRF_TIMER2->TASKS_STOP=1;NRF_TIMER2->INTENCLR=0xFFFFFFFF;NRF_TIMER2->SHORTS=0;
  NRF_TIMER2->MODE=TIMER_MODE_MODE_Timer;NRF_TIMER2->PRESCALER=4;
  NRF_TIMER2->BITMODE=TIMER_BITMODE_BITMODE_32Bit;NRF_TIMER2->TASKS_CLEAR=1;NRF_TIMER2->TASKS_START=1;
}
static uint32_t clockUs32(){NRF_TIMER2->TASKS_CAPTURE[2]=1;return NRF_TIMER2->CC[2];}
static uint64_t captureTimestamp(){
  ++clockVersion;__DMB();NRF_TIMER2->TASKS_CAPTURE[0]=1;
  uint32_t low=NRF_TIMER2->CC[0];if(low<clockLast)++clockEpoch;clockLast=low;
  uint64_t stamp=(uint64_t(clockEpoch)<<32)|low;__DMB();++clockVersion;return stamp;
}
static uint64_t monotonicUs() {
  // Foreground seqlock; capture ISR is the only epoch writer, including paused capture.
  uint32_t version,epoch,previous,low;
  do {version=clockVersion;if(version&1)continue;__DMB();epoch=clockEpoch;previous=clockLast;
    NRF_TIMER2->TASKS_CAPTURE[1]=1;low=NRF_TIMER2->CC[1];__DMB();
  } while((version&1)||version!=clockVersion);
  if(low<previous)++epoch;return (uint64_t(epoch)<<32)|low;
}

static bool imuWrite(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(IMU_ADDR); Wire.write(reg); Wire.write(value);
  return Wire.endTransmission() == 0;
}
static bool imuRead(uint8_t reg, uint8_t *out, uint8_t n) {
  Wire.beginTransmission(IMU_ADDR); Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(IMU_ADDR, n) != n) return false;
  for (uint8_t i = 0; i < n; ++i) out[i] = Wire.read();
  return true;
}
static bool beginImu() {
  uint8_t who = 0;
  if (!imuRead(IMU_WHO_AM_I, &who, 1) || who != 0x6B) return false;
  // 104 Hz XL/G, BDU enabled. FIFO continuous mode; timestamp tag is read below.
  if (!imuWrite(IMU_CTRL1_XL, 0x40) || !imuWrite(IMU_CTRL2_G, 0x40) ||
      !imuWrite(IMU_CTRL10_C, 0x20) || !imuWrite(0x12, 0x44) || !imuWrite(IMU_FIFO_CTRL1, 0x20) ||
      !imuWrite(IMU_FIFO_CTRL2, 0x00) || !imuWrite(IMU_FIFO_CTRL3, 0x44) ||
      !imuWrite(IMU_FIFO_CTRL4, 0x46)) return false;
  return true;
}
static int16_t le16(const uint8_t *p) { return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8)); }
static bool readImuFifo() {
  uint8_t status[2] = {};
  if (!imuReady || !imuRead(IMU_FIFO_STATUS1, status, 2)) return false;
  imuFifoWords = (uint16_t)status[0] | ((uint16_t)(status[1] & 0x03) << 8);
  if (imuFifoWords > 2) imuFifoWords = 2; // Timer capture preempts foreground I2C; drain faster than production.
  bool changed = false;
  for (uint16_t i = 0; i < imuFifoWords; ++i) {
    uint8_t word[7] = {};
    if (!imuRead(IMU_FIFO_DATA_OUT_TAG, word, sizeof(word))) return false;
    const uint8_t tag = word[0] >> 3;
    if (tag == 0x01) { for (uint8_t a = 0; a < 3; ++a) imuGyro[a] = le16(word + 1 + a * 2); lastGyroUpdateUs = monotonicUs(); changed = true; }
    else if (tag == 0x02) { for (uint8_t a = 0; a < 3; ++a) imuAccel[a] = le16(word + 1 + a * 2); lastAccelUpdateUs = monotonicUs(); changed = true; }
    else if (tag == 0x04) { imuTimestamp = (uint32_t)word[1] | ((uint32_t)word[2] << 8) | ((uint32_t)word[3] << 16) | ((uint32_t)word[4] << 24); }
  }
  return changed;
}
static bool queueUsb(uint8_t kind, uint64_t stamp, const uint8_t *payload, uint16_t length) {
  if (!Serial) return true;
  const uint32_t sequence = usbPacketSequence++;
  uint8_t next = (uint8_t)((usbHead + 1) % USB_QUEUE_SLOTS);
  if (next == usbTail) { ++usbDrops; return false; }
  UsbFrame &slot = usbQueue[usbHead];
  slot.bytes = encodePacket(kind, sequence, stamp, payload, length, slot.data);
  slot.offset = 0; if (!slot.bytes) { ++usbDrops; return false; }
  usbHead = next; return true;
}
static void serviceUsb() {
  if (!Serial || usbTail == usbHead) return;
  int room = Serial.availableForWrite(); if (room <= 0) return;
  UsbFrame &f = usbQueue[usbTail];
  uint16_t take = f.bytes - f.offset; if (take > (uint16_t)room) take = (uint16_t)room;
  size_t n = Serial.write(f.data + f.offset, take); f.offset += (uint16_t)n;
  if (f.offset == f.bytes) usbTail = (uint8_t)((usbTail + 1) % USB_QUEUE_SLOTS);
}
static void emitImuFrame(uint64_t stamp) {
  uint8_t p[18] = {}; put32(p, imuTimestamp); put16(p + 4, imuFifoWords);
  for (uint8_t a = 0; a < 3; ++a) { put16(p + 6 + a * 2, (uint16_t)imuGyro[a]); put16(p + 12 + a * 2, (uint16_t)imuAccel[a]); }
  if (!queueUsb(KIND_IMU, stamp, p, sizeof(p))) ++txDrops;
  queueBle(KIND_IMU, stamp, p, sizeof(p));
}

static bool uiDeadline(uint32_t budgetUs);
static void refreshUiBuffer() {} // Material label remains host metadata.
static void indicatorOff() {
 for(uint8_t i=0;i<HWPWM_MODULE_NUM;++i){
  HwPWMx[i]->removePin(LED_RED);HwPWMx[i]->removePin(LED_GREEN);HwPWMx[i]->removePin(LED_BLUE);
 }
 digitalWrite(LED_RED,HIGH);digitalWrite(LED_GREEN,HIGH);digitalWrite(LED_BLUE,HIGH);
}
static void indicatorInit() {
 pinMode(LED_RED,OUTPUT);pinMode(LED_GREEN,OUTPUT);pinMode(LED_BLUE,OUTPUT);
 digitalWrite(LED_RED,HIGH);digitalWrite(LED_GREEN,HIGH);digitalWrite(LED_BLUE,HIGH);
 analogWriteResolution(8);
}
static void serviceIndicator(uint32_t now) {
 static uint32_t due=0;if(int32_t(now-due)<0)return;due=now+20;
 if(batteryMv>0 && batteryMv<3500)lowBattery=true;
 else if(batteryMv>=3580)lowBattery=false;
 const bool streaming=!acquisitionPaused && (activeConnection!=BLE_CONN_HANDLE_INVALID || bool(Serial));
 const auto c=CuffIndicator::color(now,powerButton.boot&&powerQualified,pairingMode&&powerQualified,streaming,lowBattery||!powerQualified,captureAdcErrors!=0);
 // Seeed RGB is common-anode: low duty values illuminate the cathodes.
 analogWrite(LED_RED,255-c.r);analogWrite(LED_GREEN,255-c.g);analogWrite(LED_BLUE,255-c.b);
}
static void beginBle();
static bool detectUsbPower(){
  uint8_t enabled=0;(void)sd_softdevice_is_enabled(&enabled);
  uint32_t status=0;
  if(enabled){if(sd_power_usbregstatus_get(&status)!=NRF_SUCCESS)return false;}
  else status=NRF_POWER->USBREGSTATUS;
  return (status&POWER_USBREGSTATUS_VBUSDETECT_Msk)!=0;
}
static void servicePower(bool force=false){
  const uint32_t now=millis();
  const bool usb=detectUsbPower();
  if(force || usb!=usbPowerPresent || int32_t(now-nextBatteryMs)>=0){
    analogReadResolution(12);const uint16_t raw=analogRead(BAT_ADC_PIN);
    batteryMv=(uint16_t)((uint64_t)raw*3600ULL*1510ULL/(4095UL*510UL));nextBatteryMs=now+100;
    if(batteryMv<BATTERY_ACQUIRE_MIN_MV)batteryQualified=false;
    else if(batteryMv>=BATTERY_RESUME_MV)batteryQualified=true;
  }
  usbPowerPresent=usb;powerQualified=usbPowerPresent || batteryQualified;
}
static void serviceUi() {
  const uint32_t now=millis();
  if(!uiDeadline(300))return;
  servicePower();
  if(int32_t(now-nextUiMs)>=0){
    CuffButton::Action action=powerButton.tick((readButtons()&1)==0,now);
    if(action==CuffButton::Wake){acquisitionPaused=false;if(!bleEnabled)beginBle();refreshUiBuffer();}
    else if(action==CuffButton::Pair){pairingMode=true;pairingUntil=now+120000;acquisitionPaused=false;if(!bleEnabled)beginBle();refreshUiBuffer();}
    else if(action==CuffButton::Sleep){acquisitionPaused=true;shutdownRequested=true;return;}
    else if(action==CuffButton::Tap){acquisitionPaused=!acquisitionPaused;refreshUiBuffer();}
    if(pairingMode && int32_t(now-pairingUntil)>=0){pairingMode=false;refreshUiBuffer();}
    nextUiMs=now+10;
  }
  serviceIndicator(now);
}

// Foreground I2C is interruptible. Admit it only with at least 4 ms of free
// capture ring space; a 300 us transfer does not fit wholly inside a 250 us frame.
static bool uiDeadline(uint32_t budgetUs) {
  const uint8_t used = (uint8_t)((captureHead + CAPTURE_SLOTS - captureTail) % CAPTURE_SLOTS);
  const uint32_t freeUs = (CAPTURE_SLOTS - 1 - used) * (1000000UL / DYNAMIC_RATE_HZ);
  return freeUs > budgetUs + 4000;
}
static uint8_t readButtons() {
  uint8_t buttons=0xFF; Wire.beginTransmission(BUTTON_ADDR); Wire.write(TCA_INPUT); Wire.endTransmission();
  if (Wire.requestFrom(BUTTON_ADDR,(uint8_t)1)==1) buttons=Wire.read();
  return buttons;
}
static void initButtons() {
  Wire.beginTransmission(BUTTON_ADDR); Wire.write(TCA_OUTPUT); Wire.write(0x00); Wire.endTransmission();
  Wire.beginTransmission(BUTTON_ADDR); Wire.write(TCA_POLARITY); Wire.write(0x00); Wire.endTransmission();
  Wire.beginTransmission(BUTTON_ADDR); Wire.write(TCA_CONFIG); Wire.write(0x01); Wire.endTransmission();
}
static void stopImuForSleep() {
  if (imuReady) { imuWrite(IMU_CTRL1_XL, 0x00); imuWrite(IMU_CTRL2_G, 0x00); imuWrite(IMU_FIFO_CTRL4, 0x00); }
}
static void enterSystemOff() {
  NRF_TIMER4->TASKS_STOP=1; NRF_TIMER4->INTENCLR=0xFFFFFFFF; NVIC_DisableIRQ(TIMER4_IRQn);
  // Release buttons and clear TCA9534 IRQ before arming active-low wake.
  while ((readButtons() & 0x01) != 0x01) delay(10);
  (void)readButtons();
  stopImuForSleep(); indicatorOff();
  NRF_SPIM2->ENABLE=0;
  digitalWrite(MUX_SRCLK,LOW);digitalWrite(MUX_SER,LOW);digitalWrite(MUX_RCLK,LOW);digitalWrite(ADC_CNV,LOW);
  NRF_SPIM3->ENABLE=0;
  nrf_gpio_pin_clear(g_ADigitalPinMap[ADC_SCK]);
  pinMode(ADC_MISO, INPUT); digitalWrite(ANALOG_EN_PIN, LOW);
  delay(5);
  nrf_gpio_cfg_sense_input(9, NRF_GPIO_PIN_PULLUP, NRF_GPIO_PIN_SENSE_LOW);
  (void)sd_power_system_off();
  NRF_POWER->SYSTEMOFF = 1;
  while (true) __WFE();
}

static uint16_t readChannel(uint8_t output, uint8_t slot, uint32_t settleUs);
static void captureTimerStart() {
  NRF_TIMER4->TASKS_STOP=1; NRF_TIMER4->TASKS_CLEAR=1;
  NRF_TIMER4->MODE=TIMER_MODE_MODE_Timer;
  // nRF TIMER clock is 16 MHz. Divide by 16 => 1 MHz, 250 ticks => 4 kHz.
  NRF_TIMER4->PRESCALER=4; NRF_TIMER4->BITMODE=TIMER_BITMODE_BITMODE_32Bit;
  NRF_TIMER4->CC[0]=1000000UL/DYNAMIC_RATE_HZ;
  NRF_TIMER4->SHORTS=TIMER_SHORTS_COMPARE0_CLEAR_Msk;
  NRF_TIMER4->EVENTS_COMPARE[0]=0;
  NRF_TIMER4->INTENSET=TIMER_INTENSET_COMPARE0_Msk;
  NVIC_ClearPendingIRQ(TIMER4_IRQn); NVIC_SetPriority(TIMER4_IRQn,6);
  NVIC_EnableIRQ(TIMER4_IRQn); NRF_TIMER4->TASKS_START=1;
}
extern "C" void TIMER4_IRQHandler(void) {
  if (!NRF_TIMER4->EVENTS_COMPARE[0]) return;
  NRF_TIMER4->EVENTS_COMPARE[0]=0;
  const uint64_t captureStamp=captureTimestamp();
  const uint32_t sequence=isrCaptureSequence++; // advances even if paused/full
  if (acquisitionPaused) return;
  const uint8_t next=(uint8_t)((captureHead+1)%CAPTURE_SLOTS);
  if (next==captureTail) { ++captureDrops; return; }
  Capture &c=captureRing[captureHead];
  const uint32_t tick=(uint32_t)captureStamp;
  c.stamp=captureStamp; c.sequence=sequence; c.pressureValid=0; c.flags=0;
  const uint32_t adcBefore=captureAdcErrors;
  static uint16_t held[20]={};
  if(!powerQualified || !adcCalibrated){
    // Preserve transport/time continuity while marking every value invalid.
    c.flags=(!powerQualified?FLAG_POWER_UNQUALIFIED:0)|(!adcCalibrated?FLAG_ADC_FAULT:0);memset(held,0,sizeof(held));
    memset(c.pressure,0,sizeof(c.pressure));memset(c.dynamic,0,sizeof(c.dynamic));
    __DMB();captureHead=next;return;
  }
  for(uint8_t i=0;i<10;++i)c.dynamic[i]=readChannel(2,i,DYNAMIC_SETTLE_US);
  for(uint8_t i=0;i<10;++i)c.dynamic[i+10]=readChannel(3,i,DYNAMIC_SETTLE_US);
  if((sequence&3u)==0){
    uint8_t pi=isrPressureRoundRobin;
    held[pi]=readChannel(pi<10?0:1,pi<10?pi:pi-10,PRESSURE_SETTLE_US);
    c.pressureValid=1;c.pressureChannel=pi;isrPressureRoundRobin=(uint8_t)((pi+1)%20);
  }
  for(uint8_t i=0;i<20;++i)c.pressure[i]=held[i];
  const uint32_t elapsed=(uint32_t)(clockUs32()-tick);
  if(elapsed>captureMaxUs)captureMaxUs=elapsed;
  if(elapsed>=250 || NRF_TIMER4->EVENTS_COMPARE[0]){
    c.flags|=FLAG_TIMING_OVERRUN;++captureLateEvents;
  }
  if(captureAdcErrors!=adcBefore)c.flags|=FLAG_ADC_FAULT;
  __DMB();captureHead=next;
}

static void muxSpiBegin(){
  pinMode(MUX_RCLK,OUTPUT);digitalWrite(MUX_RCLK,LOW);
  nrf_gpio_cfg_output(g_ADigitalPinMap[MUX_SRCLK]);nrf_gpio_cfg_output(g_ADigitalPinMap[MUX_SER]);
  NRF_SPIM2->ENABLE=0;NRF_SPIM2->PSEL.SCK=g_ADigitalPinMap[MUX_SRCLK];
  NRF_SPIM2->PSEL.MOSI=g_ADigitalPinMap[MUX_SER];NRF_SPIM2->PSEL.MISO=0xFFFFFFFF;
  NRF_SPIM2->CONFIG=0;NRF_SPIM2->FREQUENCY=SPIM_FREQUENCY_FREQUENCY_M8;
  NRF_SPIM2->RXD.MAXCNT=0;NRF_SPIM2->INTENCLR=0xFFFFFFFF;NRF_SPIM2->ENABLE=SPIM_ENABLE_ENABLE_Enabled;
}
static bool selectMux(uint8_t output,uint8_t slot,uint32_t settleUs){
  alignas(4) static uint8_t address;
  if(NRF_SPIM2->ENABLE!=SPIM_ENABLE_ENABLE_Enabled){++captureAdcErrors;return false;}
  address=(slot&15)|((output&3)<<4);
  NRF_SPIM2->TXD.PTR=(uint32_t)(uintptr_t)&address;NRF_SPIM2->TXD.MAXCNT=1;
  NRF_SPIM2->EVENTS_END=0;__DMB();NRF_SPIM2->TASKS_START=1;
  uint32_t timeout=1600;while(!NRF_SPIM2->EVENTS_END && --timeout){}
  if(!timeout){CuffDma::abort(NRF_SPIM2,clockUs32);++captureAdcErrors;return false;}
  // All6 mux bits update on one latch edge after8 complete MSB-first clocks.
  nrf_gpio_pin_set(MUX_LATCH_GPIO);__NOP();__NOP();
  nrf_gpio_pin_clear(MUX_LATCH_GPIO);delayMicroseconds(settleUs);return true;
}
static void adcSpiBegin(){
  // Dedicated receive-only SPIM3: D10 is CNV, NEVER MOSI.
  NRF_SPIM3->ENABLE=0;
  NRF_SPIM3->PSEL.SCK=g_ADigitalPinMap[ADC_SCK];
  NRF_SPIM3->PSEL.MISO=g_ADigitalPinMap[ADC_MISO];
  NRF_SPIM3->PSEL.MOSI=0xFFFFFFFF;
  nrf_gpio_cfg_output(g_ADigitalPinMap[ADC_SCK]);
  nrf_gpio_cfg_input(g_ADigitalPinMap[ADC_MISO],NRF_GPIO_PIN_NOPULL);
  NRF_SPIM3->CONFIG=0;NRF_SPIM3->FREQUENCY=SPIM_FREQUENCY_FREQUENCY_M16;
  NRF_SPIM3->TXD.MAXCNT=0;NRF_SPIM3->ORC=0;NRF_SPIM3->INTENCLR=0xFFFFFFFF;
  NRF_SPIM3->ENABLE=SPIM_ENABLE_ENABLE_Enabled;
}
static bool adcRecalibrate(){
  // MCP33131D section7.1: exactly1024 SCLK pulses, including data bits,
  // in one acquisition phase with CNVST low and board-strapped SDI high.
  // Begin after initial power-up calibration/rail settling has completed.
  alignas(4) static uint8_t calibrationRx[128];
  nrf_gpio_pin_set(ADC_CNV_GPIO);delayMicroseconds(ADC_CNV_HIGH_US);
  nrf_gpio_pin_clear(ADC_CNV_GPIO);adcOutputEnableWait();
  NRF_SPIM3->RXD.PTR=(uint32_t)(uintptr_t)calibrationRx;NRF_SPIM3->RXD.MAXCNT=sizeof(calibrationRx);
  NRF_SPIM3->EVENTS_END=0;__DMB();NRF_SPIM3->TASKS_START=1;
  const uint32_t started=clockUs32();uint32_t polls=16000;
  while(!NRF_SPIM3->EVENTS_END && uint32_t(clockUs32()-started)<1000 && --polls){}
  if(!NRF_SPIM3->EVENTS_END){CuffDma::abort(NRF_SPIM3,clockUs32);++captureAdcErrors;return false;}
  NRF_SPIM3->RXD.MAXCNT=0;NRF_SPIM3->RXD.PTR=0;
  delay(700); // Maximum self-calibration650ms after the1024th clock.
  return true;
}
static uint16_t adcRead(){
  alignas(4) static uint8_t rx[2];
  if(NRF_SPIM3->ENABLE!=SPIM_ENABLE_ENABLE_Enabled){++captureAdcErrors;return 0;}
  rx[0]=rx[1]=0;
  nrf_gpio_pin_set(ADC_CNV_GPIO);delayMicroseconds(ADC_CNV_HIGH_US);
  nrf_gpio_pin_clear(ADC_CNV_GPIO);adcOutputEnableWait();
  NRF_SPIM3->RXD.PTR=(uint32_t)(uintptr_t)rx;NRF_SPIM3->RXD.MAXCNT=2;
  NRF_SPIM3->EVENTS_END=0;__DMB();NRF_SPIM3->TASKS_START=1;
  uint32_t timeout=1600;
  while(!NRF_SPIM3->EVENTS_END && --timeout){}
  if(!timeout){CuffDma::abort(NRF_SPIM3,clockUs32);++captureAdcErrors;return 0;}
  return (uint16_t(rx[0])<<8)|rx[1];
}

static uint16_t readChannel(uint8_t output, uint8_t slot, uint32_t settleUs) { return selectMux(output, slot, settleUs) ? adcRead() : 0; }

static bool queueBle(uint8_t kind, uint64_t stamp, const uint8_t *payload, uint16_t length) {
  if (!bleEnabled || activeConnection == BLE_CONN_HANDLE_INVALID || appliedBleSessionEpoch!=bleSessionEpoch) return true;
  const uint32_t sequence = blePacketSequence++;
  uint8_t next = (uint8_t)((bleHead + 1) % BLE_QUEUE_SLOTS);
  if (next == bleTail) { ++bleDrops; return false; }
  BleFrame &slot = bleQueue[bleHead]; slot.session=bleSessionEpoch;
  slot.bytes = encodePacket(kind, sequence, stamp, payload, length, slot.data);
  slot.offset = 0; if (!slot.bytes) { ++bleDrops; return false; }
  bleHead = next; return true;
}
static uint16_t uabs16(int16_t v) { return (uint16_t)(v < 0 ? -(int32_t)v : v); }
static uint16_t isqrt64(uint64_t x) {
  uint64_t op = x, res = 0, one = 1ULL << 62;
  while (one > op) one >>= 2;
  while (one) { if (op >= res + one) { op -= res + one; res = (res >> 1) + one; } else res >>= 1; one >>= 2; }
  return res > 65535 ? 65535 : (uint16_t)res;
}
static void queueBleSelection(uint64_t stamp, uint32_t index, uint16_t flags,
                              const uint16_t *pressure, const uint16_t *dynamic) {
  if (bleRawChannel < 0) return;
  const uint8_t c = (uint8_t)bleRawChannel;
  if (rawBatchCount == 0) { rawBatchFirstIndex = index; rawBatchFirstStamp = stamp; rawBatchFlags=0; }
  rawBatchFlags|=flags;
  rawBatch[rawBatchCount++] = c < 20 ? pressure[c] : dynamic[c - 20];
  if (rawBatchCount < RAW_BATCH_SAMPLES) return;
  uint8_t p[92] = {}; put32(p, rawBatchFirstIndex); put16(p + 4, c); put16(p + 6, rawBatchFlags);
  put16(p + 8, RAW_BATCH_SAMPLES); put16(p + 10, 250);
  for (uint16_t i = 0; i < RAW_BATCH_SAMPLES; ++i) put16(p + 12 + i * 2, rawBatch[i]);
  queueBle(KIND_SELECTED_RAW, rawBatchFirstStamp, p, sizeof(p)); rawBatchCount = 0;
}
static void queueBleFeatures(uint64_t stamp, uint32_t index, uint16_t flags,
                             const uint16_t *pressure, const uint16_t *dynamic) {
  if (featureCount == 0) { featureFirstIndex = index; featureFirstStamp = stamp; featureWindowFlags=0; }
  featureWindowFlags|=flags;
  if (pressureSampleThisScan) {
    const uint8_t i = pressureSampleChannel;
    featurePressureSum[i] += (int16_t)pressure[i]; featurePressureCount[i]++;
  }
  for (uint8_t i = 0; i < 20; ++i) {
    const int16_t dv = (int16_t)dynamic[i];
    featureDynamicSum[i] += dv;
    const uint16_t av = uabs16(dv); featureDynamicSq[i] += (uint64_t)av * av;
    if (av > featureDynamicPeak[i]) featureDynamicPeak[i] = av;
  }
  ++featureCount;
  if (featureCount < FEATURE_WINDOW_SAMPLES) return;
  if (bleRawChannel < 0) {
    uint8_t p[128] = {}; put32(p, featureFirstIndex); put16(p + 4, featureWindowFlags); put16(p + 6, featureCount);
    uint16_t at = 8;
    for (uint8_t i = 0; i < 20; ++i) { const uint16_t n = featurePressureCount[i]; const int32_t mean = n ? (int32_t)(featurePressureSum[i] / n) : (int16_t)pressure[i]; put16(p + at, (uint16_t)(int16_t)mean); at += 2; }
    for (uint8_t i = 0; i < 20; ++i) put16(p + at, isqrt64(featureDynamicSq[i] / featureCount)), at += 2;
    for (uint8_t i = 0; i < 20; ++i) put16(p + at, featureDynamicPeak[i]), at += 2;
    queueBle(KIND_FEATURE, featureFirstStamp, p, sizeof(p));
  }
  memset(featurePressureSum, 0, sizeof(featurePressureSum)); memset(featurePressureCount, 0, sizeof(featurePressureCount)); memset(featureDynamicSum, 0, sizeof(featureDynamicSum));
  memset(featureDynamicSq, 0, sizeof(featureDynamicSq)); memset(featureDynamicPeak, 0, sizeof(featureDynamicPeak)); featureCount = 0;
}

static bool queueScan(uint64_t stamp, uint32_t index, uint16_t flags, const uint16_t *pressure, const uint16_t *dynamic) {
  uint8_t payload[FRAME_BYTES];
  put32(payload, index); put16(payload + 4, flags);
  put16(payload + 6, DYNAMIC_RATE_HZ); put16(payload + 8, PRESSURE_RATE_HZ);
  put16(payload + 10, (uint16_t)imuTimestamp); put16(payload + 12, (uint16_t)(imuTimestamp >> 16));
  uint16_t at = 14;
  for (uint8_t i = 0; i < 20; ++i) { put16(payload + at, pressure[i]); at += 2; }
  for (uint8_t i = 0; i < 20; ++i) { put16(payload + at, dynamic[i]); at += 2; }
  const bool usbOk = queueUsb(KIND_SCAN, stamp, payload, FRAME_BYTES);
  queueBleSelection(stamp, index, flags, pressure, dynamic);
  queueBleFeatures(stamp, index, flags, pressure, dynamic);
  return usbOk;
}

static bool acquireScan() {
  if (captureTail == captureHead) return false;
  Capture c; const uint8_t tail=captureTail; __DMB(); memcpy(&c,&captureRing[tail],sizeof(c)); captureTail=(uint8_t)((tail+1)%CAPTURE_SLOTS);
  pressureSampleThisScan = c.pressureValid; pressureSampleChannel = c.pressureChannel;
  static uint32_t expected=0;
  uint16_t flags=FLAG_MUX_SETTLE_UNVERIFIED|c.flags;
  if(c.sequence!=expected){flags|=FLAG_TX_DROP;rawBatchCount=0;featureCount=0;
    memset(featurePressureSum,0,sizeof(featurePressureSum));memset(featurePressureCount,0,sizeof(featurePressureCount));
    memset(featureDynamicSq,0,sizeof(featureDynamicSq));memset(featureDynamicPeak,0,sizeof(featureDynamicPeak));}
  expected=c.sequence+1;
  const uint64_t imuNow=monotonicUs();
  if(!imuReady || !lastGyroUpdateUs || !lastAccelUpdateUs ||
     imuNow-lastGyroUpdateUs>100000 || imuNow-lastAccelUpdateUs>100000)flags|=FLAG_IMU_STALE;
  if(!queueScan(c.stamp,c.sequence,flags,c.pressure,c.dynamic))++txDrops;
  return true;
}

static void resetBleWindows() {
  rawBatchCount=0;rawBatchFlags=0;featureCount=0;featureWindowFlags=0;
  memset(featurePressureSum,0,sizeof(featurePressureSum));memset(featurePressureCount,0,sizeof(featurePressureCount));
  memset(featureDynamicSum,0,sizeof(featureDynamicSum));memset(featureDynamicSq,0,sizeof(featureDynamicSq));
  memset(featureDynamicPeak,0,sizeof(featureDynamicPeak));
}
static void onBleConnect(uint16_t handle) {
  ++bleSessionEpoch;activeConnection=handle;
  BLEConnection *c=Bluefruit.Connection(handle);
  if(!c){activeConnection=BLE_CONN_HANDLE_INVALID;return;}
  bond_keys_t keys;
  if(!c->loadBondKey(&keys) && !pairingMode){activeConnection=BLE_CONN_HANDLE_INVALID;Bluefruit.disconnect(handle);return;}
  c->requestPairing();
  c->requestMtuExchange(247);c->requestDataLengthUpdate();c->requestPHY(BLE_GAP_PHY_2MBPS);
  c->requestConnectionParameter(6);
}
static void onBleDisconnect(uint16_t handle,uint8_t) {
  if(handle!=activeConnection)return;
  activeConnection=BLE_CONN_HANDLE_INVALID;++bleSessionEpoch;
}
static void applyBleCommand(uint8_t *data,uint16_t len) {
  if(len>6 && len<=18 && !memcmp(data,"LABEL ",6)){
    char label[13]={};bool valid=true;
    for(uint16_t i=6;i<len;++i){char c=data[i];if(!((c>='A'&&c<='Z')||(c>='0'&&c<='9')||c==' '||c=='-'||c=='/')){valid=false;break;}label[i-6]=c;}
    if(valid){memcpy(materialLabel,label,sizeof(materialLabel));refreshUiBuffer();}return;
  }
  // The on-wire grammar is exactly RAW <0..39>, FEATURES or LABEL <text>.
  if((len==5 || len==6) && !memcmp(data,"RAW ",4)){
    uint8_t n=0;
    for(uint16_t i=4;i<len;++i){if(data[i]<'0'||data[i]>'9')return;n=uint8_t(n*10+data[i]-'0');}
    if(n>=40)return;
    bleRawChannel=(int8_t)n;resetBleWindows();
  }else if(len==8 && !memcmp(data,"FEATURES",8)){
    bleRawChannel=-1;resetBleWindows();
  }
}
struct ControlMessage {uint32_t session;uint8_t length,data[32];};
static ControlMessage controlQueue[4];
static volatile uint8_t controlHead=0,controlTail=0;
static uint32_t controlDrops=0;
static void onBleWrite(uint16_t handle,BLECharacteristic*,uint8_t *data,uint16_t len){
  if(handle!=activeConnection || len>32)return;uint8_t next=(controlHead+1)%4;
  if(next==controlTail){++controlDrops;return;}
  ControlMessage &m=controlQueue[controlHead];m.session=bleSessionEpoch;m.length=len;memcpy(m.data,data,len);__DMB();controlHead=next;
}
static void serviceControl(){
  const uint32_t session=bleSessionEpoch;
  if(appliedBleSessionEpoch!=session){
    // Foreground owns multi-field accumulators. Callbacks only change the epoch.
    resetBleWindows();bleTail=bleHead;bleDelimiterPending=false;appliedBleSessionEpoch=session;
  }
  if(controlTail==controlHead)return;ControlMessage m;__DMB();memcpy(&m,&controlQueue[controlTail],sizeof(m));
  controlTail=(controlTail+1)%4;
  if(m.session==bleSessionEpoch && activeConnection!=BLE_CONN_HANDLE_INVALID)applyBleCommand(m.data,m.length);
}
static void beginBle() {
  Bluefruit.configPrphConn(247, 6, 16, 4); Bluefruit.begin(1, 0); Bluefruit.autoConnLed(false);
  Bluefruit.setName("Rocoto Tactile v3"); Bluefruit.Periph.setConnInterval(6, 12);
  Bluefruit.Periph.setConnectCallback(onBleConnect); Bluefruit.Periph.setDisconnectCallback(onBleDisconnect);
  tactileService.begin(); tactileTx.setProperties(CHR_PROPS_NOTIFY); tactileTx.setPermission(SECMODE_ENC_NO_MITM, SECMODE_NO_ACCESS);
  tactileTx.setMaxLen(244); tactileTx.begin(); tactileRx.setProperties(CHR_PROPS_WRITE | CHR_PROPS_WRITE_WO_RESP);
  tactileRx.setPermission(SECMODE_NO_ACCESS, SECMODE_ENC_NO_MITM); tactileRx.setMaxLen(32); tactileRx.setWriteCallback(onBleWrite); tactileRx.begin();
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE); Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(tactileService); Bluefruit.ScanResponse.addName(); Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.start(0); bleEnabled = true;
}
static void serviceBle() {
  if (!bleEnabled || activeConnection == BLE_CONN_HANDLE_INVALID || bleTail == bleHead) return;
  BLEConnection *c = Bluefruit.Connection(activeConnection); if (!c) return;
  if(!c->secured())return;
  uint16_t mtu = c->getMtu(); if (mtu < 23) return; uint16_t room = mtu - 3; if (room > 244) room = 244;
  BleFrame &f=bleQueue[bleTail];
  if(f.session!=bleSessionEpoch){bleTail=(uint8_t)((bleTail+1)%BLE_QUEUE_SLOTS);return;}
  uint16_t take=f.bytes-f.offset;if(take>room)take=room;
  uint8_t delimiter=0;uint16_t n=bleDelimiterPending?1:take;
  ble_gatts_hvx_params_t hvx={};hvx.handle=tactileTx.handles().value_handle;
  hvx.type=BLE_GATT_HVX_NOTIFICATION;hvx.p_len=&n;hvx.p_data=bleDelimiterPending?&delimiter:f.data+f.offset;
  const uint32_t status=sd_ble_gatts_hvx(activeConnection,&hvx);
  if(status==NRF_SUCCESS){
    if(bleDelimiterPending){if(n)bleDelimiterPending=false;return;}
    f.offset+=n;if(f.offset==f.bytes)bleTail=(uint8_t)((bleTail+1)%BLE_QUEUE_SLOTS);
  }else if(status!=NRF_ERROR_RESOURCES && status!=NRF_ERROR_BUSY && !bleDelimiterPending){
    // Discard once; delimit any already-delivered prefix before the next frame.
    ++bleDrops;bleDelimiterPending=f.offset!=0;bleTail=(uint8_t)((bleTail+1)%BLE_QUEUE_SLOTS);
  }
}

static void sendHealth() {
  uint8_t p[42] = {};
  put32(p, captureLateEvents); put32(p + 4, captureAdcErrors); put32(p + 8, usbDrops + captureDrops);
  put32(p + 12, imuReady ? 0x6B : 0); put32(p + 16, imuTimestamp); put32(p + 20, captureMaxUs);
  put32(p+24,bleDrops);put32(p+28,captureDrops);put16(p+32,batteryMv);
  put16(p+34,(acquisitionPaused?1:0)|(pairingMode?2:0)|(!powerQualified?4:0)|(usbPowerPresent?8:0));
  put16(p+36,ADC_REFERENCE_MV);put16(p+38,ADC_MIDPOINT_MV);put16(p+40,SENSOR_EXCITATION_MV);
  const uint64_t stamp = monotonicUs();
  queueUsb(KIND_HEALTH, stamp, p, sizeof(p));
  queueBle(KIND_HEALTH, stamp, p, sizeof(p));
}

static void configureNfcGpio(){
  if(NRF_UICR->NFCPINS & UICR_NFCPINS_PROTECT_Msk){
    NRF_NVMC->CONFIG=NVMC_CONFIG_WEN_Wen;while(!NRF_NVMC->READY){}
    NRF_UICR->NFCPINS &= ~UICR_NFCPINS_PROTECT_Msk;while(!NRF_NVMC->READY){}
    NRF_NVMC->CONFIG=NVMC_CONFIG_WEN_Ren;NVIC_SystemReset();
  }
}
void setup() {
  clockBegin();
  const bool wakeFromOff=(NRF_POWER->RESETREAS & POWER_RESETREAS_OFF_Msk)!=0;
  NRF_POWER->RESETREAS=POWER_RESETREAS_OFF_Msk;
  powerButton.begin(wakeFromOff,millis());acquisitionPaused=wakeFromOff;
  pinMode(BAT_ENABLE_PIN,OUTPUT);digitalWrite(BAT_ENABLE_PIN,LOW);
  digitalWrite(PIN_CHARGING_CURRENT,LOW);pinMode(PIN_CHARGING_CURRENT,OUTPUT); //100mA: selected500mAh cell standard0.2C; retain inSystemOFF.
  digitalWrite(PIN_LSM6DS3TR_C_POWER,LOW);pinMode(PIN_LSM6DS3TR_C_POWER,OUTPUT);
  digitalWrite(PIN_PDM_PWR,LOW);pinMode(PIN_PDM_PWR,OUTPUT);
  configureNfcGpio();
  digitalWrite(ADC_CNV,LOW);pinMode(ADC_CNV,OUTPUT);
  digitalWrite(MUX_SRCLK,LOW);pinMode(MUX_SRCLK,OUTPUT);
  digitalWrite(MUX_SER,LOW);pinMode(MUX_SER,OUTPUT);
  digitalWrite(MUX_RCLK,LOW);pinMode(MUX_RCLK,OUTPUT);
  pinMode(ANALOG_EN_PIN, OUTPUT); digitalWrite(ANALOG_EN_PIN, HIGH); delay(5);
  muxSpiBegin();
  pinMode(ADC_CNV, OUTPUT); digitalWrite(ADC_CNV, LOW);
  // XIAO nRF52840 Sense maps Wire to D4/D5 (I2C_SDA/I2C_SCL).
  Serial.begin(2000000); Wire.begin(); Wire.setClock(400000); initButtons();
  indicatorInit(); adcSpiBegin(); imuReady = beginImu();
  // Qualify wake before the700ms ADC startup wait: otherwise a short wake
  // pulse could be mistaken for a long hold while setup blocks.
  while(wakeFromOff && powerButton.boot && !shutdownRequested){serviceUi();delay(1);}
  if(shutdownRequested)enterSystemOff();
  if(!wakeFromOff){pairingMode=true;pairingUntil=millis()+120000;beginBle();}
  // DS20005947B table 1-1: power-up self-calibration maximum 650 ms.
  // Reference/analog rails have already started; allow 700 ms before conversion.
  delay(700); adcCalibrated=adcRecalibrate(); servicePower(true); captureTimerStart(); pinMode(BAT_ENABLE_PIN,OUTPUT); digitalWrite(BAT_ENABLE_PIN,LOW); analogReadResolution(12); nextScanUs = monotonicUs();
}
void loop() {
  const uint64_t now = monotonicUs();
  serviceControl(); serviceUsb(); serviceBle(); serviceUi();
  if (shutdownRequested) { enterSystemOff(); }
  for (uint8_t i=0; i<8 && acquireScan(); ++i) { serviceUsb(); }
  if (imuReady && now >= nextImuReadUs && uiDeadline(300)) { if (readImuFifo()) emitImuFrame(now); nextImuReadUs = now + 2000; }
  static uint64_t nextHealth = 0;
  if (now >= nextHealth) { sendHealth(); nextHealth = now + 1000000; }
  if (Serial.available()) { char c = (char)Serial.read(); if (c == 'S') nextScanUs = monotonicUs(); }
}
