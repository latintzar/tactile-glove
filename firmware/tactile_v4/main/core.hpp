#pragma once
#include <atomic>
#include <cstdint>
#include <cstring>
#include <algorithm>
#ifndef IRAM_ATTR
#define IRAM_ATTR
#endif
#include "../../tactile_v3/tactile_v3_protocol.h"
#include "../../tactile_v3/button_control.h"
namespace V4 {
using namespace TactileV3;
constexpr uint32_t SCAN_US=250, IMU_ODR_HZ=833;
constexpr uint16_t DYNAMIC_SETTLE_US=6, PRESSURE_SETTLE_US=24;
constexpr uint8_t KIND_IMU_FIFO=6, KIND_V4_STATUS=7, KIND_LABEL=8, KIND_BROWSER_STATUS=9;
constexpr uint16_t CAMERA_TIMESTAMP_FIRST_DMA=1;
struct Pins {
 static constexpr int camera[12]={11,9,8,10,12,18,17,16,15,13,6,7};
 static constexpr int sda=4,scl=5,adcClock=39,adcData=40,adcCnv=41;
 static constexpr int muxClock=43,muxData=42,muxLatch=38;
 static constexpr int sdClock=14,sdMosi=21,sdMiso=47,sdCs=48;
 static constexpr int analogEnable=44,button=2,battery=1;
};
struct Capture { uint64_t stamp; uint32_t index; uint16_t flags,pressure[20],dynamic[20]; uint8_t pressureChannel,pressureValid; };
// ESP32-S3 aligned 32-bit loads/stores are atomic. Each queue counter has one
// writer. MEMW orders payload publication across cores; no ISR lock/RMW helper.
template<class T> struct Cell {
#ifdef ESP_PLATFORM
 alignas(4) volatile T value;
 constexpr Cell(T v):value(v){}
 T IRAM_ATTR load(std::memory_order=std::memory_order_seq_cst)const {T v=value;asm volatile("memw":::"memory");return v;}
 void IRAM_ATTR store(T v,std::memory_order=std::memory_order_seq_cst){asm volatile("memw":::"memory");value=v;}
 T IRAM_ATTR fetch_add(T n){T old=value;store(old+n);return old;}
#else
 std::atomic<T> value;
 constexpr Cell(T v):value(v){}
 T load(std::memory_order m=std::memory_order_seq_cst)const{return value.load(m);}
 void store(T v,std::memory_order m=std::memory_order_seq_cst){value.store(v,m);}
 T fetch_add(T n){return value.fetch_add(n);}
#endif
 Cell& operator=(T v){store(v);return *this;}operator T()const{return load();}
};
template<class T,uint32_t N> struct Ring {
 static_assert((N&(N-1))==0,"power-of-two queue");
 T items[N]{}; Cell<uint32_t> head{0},tail{0};
 bool IRAM_ATTR push(const T& v) { const uint32_t h=head.load(std::memory_order_relaxed); if(h-tail.load(std::memory_order_acquire)==N)return false;items[h&(N-1)]=v;head.store(h+1,std::memory_order_release);return true; }
 bool pop(T& v) { const uint32_t t=tail.load(std::memory_order_relaxed);if(t==head.load(std::memory_order_acquire))return false;v=items[t&(N-1)];tail.store(t+1,std::memory_order_release);return true; }
};
struct Acquisition {
 Ring<Capture,128> ring;uint16_t held[20]{};uint8_t pressureNext=0;
 Cell<uint32_t> drops{0},late{0},faults{0},maxUs{0};
 Cell<bool> enabled{false},qualified{false},calibrated{false},active{false};
 template<class ADC> void IRAM_ATTR capture(uint64_t stamp,uint32_t index,ADC& adc) {
  active.store(true);if(!enabled.load(std::memory_order_relaxed)){active.store(false);return;}
  Capture c{};c.stamp=stamp;c.index=index;c.flags=FLAG_MUX_SETTLE_UNVERIFIED;
  if(!qualified.load(std::memory_order_relaxed)||!calibrated.load(std::memory_order_relaxed)) {
   if(!qualified.load())c.flags|=FLAG_POWER_UNQUALIFIED;
   if(!calibrated.load())c.flags|=FLAG_ADC_FAULT;
   for(unsigned i=0;i<20;i++)held[i]=0;
  } else {
   bool good=true;
   for(unsigned i=0;i<20;i++){uint16_t x=0;bool ok=adc.read(2+i/10,i%10,DYNAMIC_SETTLE_US,x);good=ok&&good;c.dynamic[i]=x;}
   if((index&3)==0){uint16_t x=0;bool ok=adc.read(pressureNext/10,pressureNext%10,PRESSURE_SETTLE_US,x);good=ok&&good;held[pressureNext]=x;c.pressureChannel=pressureNext;c.pressureValid=1;pressureNext=(pressureNext+1)%20;}
   for(unsigned i=0;i<20;i++)c.pressure[i]=held[i];
   if(!good){c.flags|=FLAG_ADC_FAULT;faults.fetch_add(1);calibrated.store(false);}
  }
  if(!qualified.load()){c.flags|=FLAG_POWER_UNQUALIFIED;for(unsigned i=0;i<20;i++){c.pressure[i]=0;c.dynamic[i]=0;}}
  uint32_t elapsed=uint32_t(adc.now()-stamp);if(elapsed>maxUs.load())maxUs.store(elapsed);
  if(elapsed>=SCAN_US){c.flags|=FLAG_TIMING_OVERRUN;late.fetch_add(1);}
  if(!ring.push(c)){drops.fetch_add(1);}
  active.store(false);
 }
};
inline uint32_t integerSqrt(uint64_t v){uint64_t r=0,b=uint64_t(1)<<62;while(b>v)b>>=2;while(b){if(v>=r+b){v-=r+b;r=(r>>1)+b;}else r>>=1;b>>=2;}return uint32_t(r);}
struct Features {
 uint64_t squares[20]{};int64_t pressureSum[20]{};uint16_t peak[20]{},pressureN[20]{};
 uint16_t n=0,flags=0;uint32_t first=0,expected=0;uint64_t stamp=0;bool haveExpected=false;
 void reset(){*this=Features{};}
 bool add(const Capture& c,uint8_t out[128]){
  if(haveExpected && c.index!=expected){reset();}
  haveExpected=true;expected=c.index+1;
  if(!n){first=c.index;stamp=c.stamp;}flags|=c.flags;
  if(c.pressureValid){unsigned i=c.pressureChannel;pressureSum[i]+=int16_t(c.pressure[i]);pressureN[i]++;}
  for(unsigned i=0;i<20;i++){int32_t x=int16_t(c.dynamic[i]);uint32_t a=x<0?-x:x;squares[i]+=uint64_t(a)*a;peak[i]=std::max<uint16_t>(peak[i],a);}
  if(++n<80)return false;
  put32(out,first);put16(out+4,flags);put16(out+6,n);
  for(unsigned i=0;i<20;i++){put16(out+8+2*i,pressureN[i]?int16_t(pressureSum[i]/pressureN[i]):c.pressure[i]);put16(out+48+2*i,integerSqrt(squares[i]/n));put16(out+88+2*i,peak[i]);}
  return true;
 }
};
struct Command {
 enum Kind { Invalid,Raw,Feature,Label }kind=Invalid;int8_t channel=-1;char label[13]{};
 static Command parse(const uint8_t* p,size_t n){Command c;
  if(n==8 && !memcmp(p,"FEATURES",8)){c.kind=Feature;return c;}
  if((n==5||n==6)&&!memcmp(p,"RAW ",4)){unsigned v=0;for(size_t i=4;i<n;i++){if(p[i]<'0'||p[i]>'9')return c;v=v*10+p[i]-'0';}if(v<40){c.kind=Raw;c.channel=v;}return c;}
  if(n>6&&n<=18&&!memcmp(p,"LABEL ",6)){for(size_t i=6;i<n;i++){char x=p[i];if(!((x>='A'&&x<='Z')||(x>='0'&&x<='9')||x==' '||x=='-'||x=='/'))return Command{};c.label[i-6]=x;}c.kind=Label;}return c;
 }
};
// CDC accepts newline-delimited commands; an overlong line is discarded whole.
struct CommandLine {
 uint8_t bytes[31]{};uint8_t size=0;bool overflow=false;
 void reset(){size=0;overflow=false;}
 bool feed(uint8_t byte,uint8_t out[32]){if(byte=='\r')return false;if(byte=='\n'){bool valid=!overflow&&size&&Command::parse(bytes,size).kind!=Command::Invalid;if(valid){out[0]=size;memcpy(out+1,bytes,size);}reset();return valid;}if(size<sizeof(bytes))bytes[size++]=byte;else overflow=true;return false;}
};
// A session label stays in RAM and is repeated in recordings/status until changed.
struct LabelState {
 char text[13]{};
 bool apply(const Command& command){if(command.kind!=Command::Label)return false;memcpy(text,command.label,sizeof(text));return true;}
 void payload(uint8_t out[13])const{memcpy(out,text,sizeof(text));}
};
constexpr unsigned IMU_FIFO_CAPACITY=512;
struct FifoStatus {
 unsigned count;bool overrun,invalid;
 static FifoStatus decode(uint8_t low,uint8_t high){unsigned n=low|((high&3u)<<8);return {n,bool(high&0x48u),n>IMU_FIFO_CAPACITY};}
};
// Software capture qualification is separate from the USB500mA hardware latch.
inline bool highCurrentUsb(uint8_t io1,bool valid){return valid&&!(io1&(1u<<3))&&!(io1&1u);}
struct ExpanderState {
 uint16_t confirmed=0;
 template<class Write> bool update(uint16_t set,uint16_t clear,Write write){uint16_t next=(confirmed|set)&~clear;if(!write(next))return false;confirmed=next;return true;}
};
// ST AN5398 section9.11: preserve raw seven-byte FIFO words and timestamp tags.
// Every batch includes a contemporaneous sensor-clock/MCU-clock anchor. The
// host maps timestamp tags; FIFO read time is never relabeled as sample time.
struct PowerGate {
 bool qualified=false,stopRequested=false;
 // Once capture has been qualified, losing its supply evidence requests the
 // complete camera/storage shutdown. A fresh boot is required to requalify.
 bool update(uint16_t mv,bool adcOk,bool usbAdequate){
  bool next=adcOk&&(mv>=(qualified?3200:3550)||usbAdequate);
  if(qualified&&!next)stopRequested=true;
  qualified=next&&!stopRequested;
  return qualified;
 }
};
struct ImuAnchor {
 uint32_t sensorTicks=0;uint64_t midpointUs=0;uint32_t uncertaintyUs=0;
 bool set(uint32_t ticks,uint64_t before,uint64_t after){if(after<before||after-before>5000)return false;sensorTicks=ticks;midpointUs=before+(after-before)/2;uncertaintyUs=uint32_t((after-before+1)/2)+25;return true;}
 bool map(uint32_t ticks,uint64_t& stamp)const {int64_t d=int64_t(int32_t(ticks-sensorTicks))*25;int64_t result=int64_t(midpointUs)+d;if(result<0)return false;stamp=uint64_t(result);return true;}
};
inline uint16_t imuPayload(uint8_t*out,const ImuAnchor&a,uint16_t flags,const uint8_t*words,uint8_t count,uint8_t source=0){
 if(count>28){return 0;}
 put32(out,a.sensorTicks);for(unsigned i=0;i<8;i++)out[4+i]=uint8_t(a.midpointUs>>(8*i));put32(out+12,a.uncertaintyUs);put16(out+16,flags);out[18]=count;out[19]=source;put16(out+20,833);out[22]=4;out[23]=2;memcpy(out+24,words,7*count);return 24+7*count;
}
// Pinned ov5640.c VGA/JPEG clock tree at24MHz XCLK: SYSCLK54MHz,
// HTS2060. VTS2622 yields9.997556fps. Keep PLL untouched; verify the
// expected tree before changing documented timing/night-mode registers.
constexpr uint32_t CAMERA_SYSCLK_HZ=54000000;
constexpr uint16_t CAMERA_HTS=2060,CAMERA_VTS=2622;
template<class Read,class Write> bool configureCameraTiming(Read read,Write write){
 const unsigned expected[][3]={{0x3034,0x0F,0x0A},{0x3035,0xF0,0x40},{0x3036,0xFF,180},{0x3037,0x1F,2},{0x3108,0x3F,0x26},{0x380C,0xFFFF,CAMERA_HTS}};
 for(const auto& r:expected)if(read(r[0],r[1])!=int(r[2]))return false;
 return write(0x380E,0xFFFF,CAMERA_VTS)==0&&write(0x3A00,0x04,0)==0&&read(0x380E,0xFFFF)==CAMERA_VTS&&read(0x3A00,0x04)==0;
}
// Continuous capture with a10fps output schedule. Faster source frames are
// returned immediately; actual source timestamps and skipped-frame counts remain.
struct CameraPacer {
 static constexpr uint64_t PERIOD_US=100000;
 uint64_t next=0;bool started=false;
 bool accept(uint64_t stamp){if(started&&stamp<next)return false;if(!started){next=stamp;started=true;}next+=((stamp-next)/PERIOD_US+1)*PERIOD_US;return true;}
};
inline uint32_t crc32(const uint8_t*p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xEDB88320u&uint32_t(-int32_t(c&1)));}return ~c;}
// JPEG record: 32byte header then exactly jpegBytes bytes. All integer fields LE.
inline void jpegHeader(uint8_t out[32],uint32_t seq,uint64_t stamp,uint32_t bytes,uint32_t dataCrc,uint16_t width,uint16_t height){
 memset(out,0,32);memcpy(out,"GV4J",4);put32(out+4,seq);for(unsigned i=0;i<8;i++)out[8+i]=uint8_t(stamp>>(8*i));put32(out+16,bytes);put32(out+20,dataCrc);put16(out+24,width);put16(out+26,height);put16(out+28,CAMERA_TIMESTAMP_FIRST_DMA);put16(out+30,crc16(out,30));
}
inline void scanPayload(uint8_t*p,const Capture&c){put32(p,c.index);put16(p+4,c.flags);put16(p+6,4000);put16(p+8,50);put32(p+10,0);for(unsigned i=0;i<20;i++){put16(p+14+2*i,c.pressure[i]);put16(p+54+2*i,c.dynamic[i]);}}
// Shared by the target task and native regression harness. Feature windows run
// continuously while a selected waveform is added; BLE retains one data mode.
struct CapturePackets {
 Features features; int raw=-1; uint16_t rawN=0,rawFlags=0;
 uint64_t rawStamp=0; uint32_t rawIndex=0,expected=0;
 bool haveExpected=false; uint8_t rawPayload[92]{};
 bool command(const Command& c){
  if(c.kind==Command::Raw)raw=c.channel;
  else if(c.kind==Command::Feature)raw=-1;
  else return false;
  rawN=0;return true;
 }
 template<class Emit> void add(Capture c,Emit emit){
  if(haveExpected&&c.index!=expected){c.flags|=FLAG_TX_DROP;features.reset();rawN=0;}
  expected=c.index+1;haveExpected=true;
  uint8_t p[128];scanPayload(p,c);emit(KIND_SCAN,c.stamp,p,94,false);
  if(features.add(c,p)){emit(KIND_FEATURE,features.stamp,p,128,raw<0);features.reset();}
  if(raw<0)return;
  if(!rawN){rawStamp=c.stamp;rawIndex=c.index;rawFlags=0;}
  rawFlags|=c.flags;uint16_t value=raw<20?c.pressure[raw]:c.dynamic[raw-20];
  put16(rawPayload+12+2*rawN,value);
  if(++rawN==40){put32(rawPayload,rawIndex);put16(rawPayload+4,raw);put16(rawPayload+6,rawFlags);put16(rawPayload+8,40);put16(rawPayload+10,250);emit(KIND_SELECTED_RAW,rawStamp,rawPayload,sizeof(rawPayload),true);rawN=0;}
 }
};

}
