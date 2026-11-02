#include "../../firmware/tactile_v4/main/core.hpp"
#include "../../firmware/tactile_v4/main/shutdown.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
#include <thread>
#include <sstream>
#include <vector>
#include <map>
using namespace V4;
static_assert(DYNAMIC_SETTLE_US==6&&PRESSURE_SETTLE_US==24,"V4 acquisition settle contract");
struct FakeADC {uint64_t time=0;bool failure=false;unsigned pressure[20]{};unsigned dynamic[20]{};uint64_t now(){return time;}bool read(unsigned bank,unsigned slot,unsigned settle,uint16_t&out){time+=settle+3;if(bank<2)pressure[bank*10+slot]++;else dynamic[(bank-2)*10+slot]++;out=failure?0:uint16_t((bank*10+slot)*7-200);return !failure;}};
struct WaveADC {uint64_t time=0;int16_t value=0;uint64_t now(){return time;}bool read(unsigned bank,unsigned slot,unsigned settle,uint16_t&out){time+=settle+3;out=(bank==2&&slot==0)?uint16_t(value):0;return true;}};
struct FaultShutdownIO {
 unsigned fail=0;std::vector<unsigned> calls;
 bool call(unsigned phase){calls.push_back(phase);return phase!=fail;}
 bool stopImus(){return call(1);}bool resetCamera(){return call(2);}bool stopClock(){return call(3);}
 bool disableInterface(){return call(4);}bool disableCore(){return call(5);}bool disableAnalog(){return call(6);}bool disableFinalRails(){return call(7);}
};
int main(int argc,char**argv){unsigned checks=0;Acquisition a;FakeADC adc;Capture c{};a.enabled=true;a.qualified=true;a.calibrated=true;uint8_t p[128],wire[256];Features features;unsigned windows=0;
 std::ofstream stream(argc>1?argv[1]:"v4-actual-core.bin",std::ios::binary);
 for(unsigned i=0;i<4000;i++){adc.time=uint64_t(i)*250;a.capture(adc.time,i,adc);assert(a.ring.pop(c));assert(c.index==i&&c.stamp==uint64_t(i)*250);assert(!(c.flags&FLAG_TIMING_OVERRUN));scanPayload(p,c);auto n=encodePacket(KIND_SCAN,i,c.stamp,p,94,wire);stream.write((char*)wire,n);if(features.add(c,p)){windows++;assert(get16(p+6)==80);features.reset();}}
 for(unsigned i=0;i<20;i++){assert(adc.dynamic[i]==4000);assert(adc.pressure[i]==50);}assert(windows==50);checks++;
 a.qualified=false;adc.time=1000000;a.capture(adc.time,4000,adc);assert(a.ring.pop(c));assert(c.flags&FLAG_POWER_UNQUALIFIED);for(auto v:c.pressure)assert(v==0);for(auto v:c.dynamic)assert(v==0);checks++;
 a.qualified=true;adc.failure=true;adc.time+=250;a.capture(adc.time,4001,adc);assert(a.ring.pop(c));assert(c.flags&FLAG_ADC_FAULT);assert(!a.calibrated.load());checks++;
 a.calibrated=true;adc.failure=false;for(unsigned i=0;i<140;i++){adc.time+=250;a.capture(adc.time,i,adc);}assert(a.drops.load()==12);while(a.ring.pop(c)){}checks++;
 Ring<uint32_t,8> ring;ring.head.store(0xFFFFFFFCu);ring.tail.store(0xFFFFFFFCu);for(unsigned i=0;i<8;i++)assert(ring.push(i));assert(!ring.push(9));for(unsigned i=0;i<8;i++){uint32_t x;assert(ring.pop(x)&&x==i);}checks++;
 Ring<uint32_t,64> threaded;std::thread producer([&]{for(unsigned i=0;i<100000;i++)while(!threaded.push(i))std::this_thread::yield();});for(unsigned i=0;i<100000;i++){uint32_t x;while(!threaded.pop(x))std::this_thread::yield();assert(x==i);}producer.join();checks++;
 for(auto invalid:{"RAW -1","RAW 40","RAW 4x","RAW 1\n","FEATURE","LABEL bad","LABEL ","LABEL ABCDEFGHIJKLM"}){assert(Command::parse((const uint8_t*)invalid,strlen(invalid)).kind==Command::Invalid);}
 assert(Command::parse((const uint8_t*)"RAW 39",6).channel==39);assert(Command::parse((const uint8_t*)"FEATURES",8).kind==Command::Feature);checks++;
 ImuAnchor anchor;assert(anchor.set(0xFFFFFFF0u,999900,1000100));uint64_t stamp;assert(anchor.map(0x10,stamp)&&stamp==1000800);assert(anchor.uncertaintyUs==125);assert(!anchor.set(1,100,99));assert(!anchor.set(1,0,5001));checks++;
 uint8_t words[196]{};words[0]=4<<3;put32(words+1,0x10);assert(imuPayload(p,anchor,1,words,2)==38);assert(get16(p+16)==1&&p[18]==2&&p[19]==0&&get16(p+20)==833&&p[22]==4&&p[23]==2);assert(imuPayload(p,anchor,4,words,2,1)==38&&p[19]==1);assert(imuPayload(p,anchor,0,words,29)==0);checks++;
 uint8_t h[32];const uint8_t jpeg[]={255,216,1,2,255,217};jpegHeader(h,7,0x100000001ULL,sizeof(jpeg),crc32(jpeg,sizeof(jpeg)),640,480);assert(!memcmp(h,"GV4J",4));assert(get32(h+4)==7&&get32(h+8)==1&&get32(h+12)==1);assert(get16(h+30)==crc16(h,30));assert(crc32((const uint8_t*)"123456789",9)==0xCBF43926);checks++;
 CuffButton::Control b;b.begin(true,0);assert(b.tick(true,3000)==CuffButton::Pair);assert(b.tick(true,5000)==CuffButton::None);b.tick(false,5010);assert(b.tick(false,5040)==CuffButton::None);checks++;
 Features f;Capture v{};v.dynamic[0]=0x8000;v.index=0;assert(!f.add(v,p));v.index=1;v.flags=FLAG_POWER_UNQUALIFIED;assert(!f.add(v,p));for(unsigned i=2;i<80;i++){v.index=i;v.flags=0;bool done=f.add(v,p);assert(done==(i==79));}assert(get16(p+4)&FLAG_POWER_UNQUALIFIED);assert(get16(p+48)==32768&&get16(p+88)==32768);checks++;
 f.reset();v.index=0;f.add(v,p);v.index=7;f.add(v,p);assert(f.n==1&&f.first==7);checks++;
 PowerGate power;assert(!power.update(3549,true,false)&&!power.stopRequested);assert(power.update(3550,true,false));assert(power.update(3200,true,false));assert(!power.update(3199,true,false)&&power.stopRequested);assert(!power.update(4200,true,true));checks++;
 // Failed ADC/calibration and USB loss after valid startup must request shutdown,
 // including when the reported battery is zero rather than a plausible low value.
 for(bool adcFailure:{false,true}){PowerGate loss;assert(loss.update(0,true,true));assert(!loss.update(0,!adcFailure,false)&&loss.stopRequested);assert(!loss.update(4200,true,true));}checks++;
 PowerGate measurement;assert(measurement.update(4200,true,true));assert(!measurement.update(4200,false,true)&&measurement.stopRequested);checks++;
 PowerGate startup;assert(!startup.update(0,false,false)&&!startup.stopRequested);assert(!startup.update(3000,true,false)&&!startup.stopRequested);assert(startup.update(3600,true,false));assert(startup.update(0,true,true));assert(startup.update(3300,true,false)&&!startup.stopRequested);checks++;
 LabelState label;assert(!label.apply(Command::parse((const uint8_t*)"FEATURES",8)));assert(label.apply(Command::parse((const uint8_t*)"LABEL TEST/1",12)));uint8_t labelBytes[13];label.payload(labelBytes);assert(!strcmp((const char*)labelBytes,"TEST/1"));assert(labelBytes[12]==0);assert(!label.apply(Command::parse((const uint8_t*)"LABEL bad",9)));label.payload(labelBytes);assert(!strcmp((const char*)labelBytes,"TEST/1"));checks++;
 auto full=FifoStatus::decode(0,2);assert(full.count==512&&!full.invalid);auto impossible=FifoStatus::decode(1,2);assert(impossible.invalid);assert(FifoStatus::decode(0,0x08).overrun);assert(FifoStatus::decode(0,0x40).overrun);checks++;
 ExpanderState expander;unsigned writes=0;assert(expander.update(0x103,0,[&](uint16_t x){writes++;return x==0x103;}));assert(expander.confirmed==0x103);assert(!expander.update(0x800,0x100,[&](uint16_t){writes++;return false;}));assert(expander.confirmed==0x103);assert(expander.update(0x800,0x100,[&](uint16_t x){writes++;return x==0x803;}));assert(expander.confirmed==0x803&&writes==3);checks++;
 assert(!highCurrentUsb(0xFF,true));assert(!highCurrentUsb(1,true));assert(!highCurrentUsb(0,false));assert(!highCurrentUsb(8,true));assert(highCurrentUsb(0,true));assert(highCurrentUsb(2,true));PowerGate legacy;assert(!legacy.update(0,true,highCurrentUsb(1,true)));assert(legacy.update(3550,true,false));assert(!legacy.update(3199,true,false));checks++;
 CommandLine line;uint8_t command[32]{};for(char x:std::string("RAW 39\r"))assert(!line.feed(x,command));assert(line.feed('\n',command));assert(command[0]==6&&!memcmp(command+1,"RAW 39",6));for(unsigned i=0;i<64;i++)line.feed('A',command);assert(!line.feed('\n',command));for(char x:std::string("LABEL NEXT"))line.feed(x,command);line.reset();assert(!line.feed('\n',command));for(char x:std::string("FEATURES"))line.feed(x,command);assert(line.feed('\n',command)&&command[0]==8);checks++;
 std::string prefix=argc>1?argv[1]:"v4-actual-core.bin";std::ofstream extra(prefix+".imu-status",std::ios::binary);
 for(uint8_t source=0;source<2;source++){uint8_t payload[220];uint16_t n=imuPayload(payload,anchor,4,words,2,source);uint16_t encoded=encodePacket(KIND_IMU_FIFO,9000+source,anchor.midpointUs,payload,n,wire);extra.write((char*)wire,encoded);}
 uint8_t status[32]{};put32(status,0xA4715A4E);put32(status+16,833);put32(status+28,1);uint16_t encoded=encodePacket(KIND_V4_STATUS,9002,1000000,status,32,wire);extra.write((char*)wire,encoded);
 std::ofstream labels(prefix+".label",std::ios::binary);encoded=encodePacket(KIND_LABEL,9003,1000001,labelBytes,13,wire);labels.write((char*)wire,encoded);
 std::ofstream video(prefix+".jpeg",std::ios::binary);video.write((char*)h,32);video.write((char*)jpeg,sizeof(jpeg));
 if(argc>2){std::ifstream csv(argv[2]);assert(csv.good());std::string line;std::getline(csv,line);assert(line=="scan_index,dynamic_code,pressure_code");Acquisition piezo;piezo.enabled=true;piezo.qualified=true;piezo.calibrated=true;WaveADC wave;Features waveFeatures;std::ofstream output(prefix+".piezo",std::ios::binary);unsigned scans=0,windows=0,sequence=0;while(std::getline(csv,line)){if(line.empty())continue;std::replace(line.begin(),line.end(),',',' ');std::istringstream values(line);unsigned index;int dynamic,pressure;values>>index>>dynamic>>pressure;assert(values&&index==scans&&pressure==0&&dynamic>=-32768&&dynamic<=32767);wave.time=uint64_t(index)*250;wave.value=dynamic;piezo.capture(wave.time,index,wave);Capture sample{};assert(piezo.ring.pop(sample)&&int16_t(sample.dynamic[0])==dynamic);for(unsigned i=1;i<20;i++)assert(sample.dynamic[i]==0);uint8_t payload[128],bytes[256];scanPayload(payload,sample);uint16_t n=encodePacket(KIND_SCAN,sequence++,sample.stamp,payload,94,bytes);output.write((char*)bytes,n);if(waveFeatures.add(sample,payload)){n=encodePacket(KIND_FEATURE,sequence++,waveFeatures.stamp,payload,128,bytes);output.write((char*)bytes,n);waveFeatures.reset();windows++;}scans++;}assert(scans==520&&windows==6);checks++;}
 CameraPacer paced;unsigned accepted=0;for(unsigned i=0;i<30;i++)if(paced.accept(uint64_t(i)*100000/3))accepted++;assert(accepted==10);CameraPacer slower;accepted=0;for(unsigned i=0;i<15;i++)if(slower.accept(uint64_t(i)*200000/3))accepted++;assert(accepted==10);assert(slower.accept(3000000));assert(!slower.accept(3000001));checks++;
 std::map<unsigned,int> cameraRegs={{0x3034,0x1A},{0x3035,0x41},{0x3036,180},{0x3037,2},{0x3108,0x26},{0x380C,2060},{0x380E,984},{0x3A00,0x7C}};auto readCamera=[&](unsigned reg,unsigned mask){return cameraRegs[reg]&int(mask);};auto writeCamera=[&](unsigned reg,unsigned mask,unsigned value){cameraRegs[reg]=(cameraRegs[reg]&~mask)|(value&mask);return 0;};assert(configureCameraTiming(readCamera,writeCamera));assert(cameraRegs[0x380E]==2622&&!(cameraRegs[0x3A00]&4));assert(CAMERA_SYSCLK_HZ/(double(CAMERA_HTS)*CAMERA_VTS)>9.99&&CAMERA_SYSCLK_HZ/(double(CAMERA_HTS)*CAMERA_VTS)<10.0);cameraRegs[0x380C]=2000;assert(!configureCameraTiming(readCamera,writeCamera));cameraRegs[0x380C]=2060;assert(!configureCameraTiming(readCamera,[](unsigned,unsigned,unsigned){return -1;}));checks++;
 std::ofstream dualMode(prefix+".dual-mode",std::ios::binary);unsigned dualSequence=0;CapturePackets pipeline;Command selection=Command::parse((const uint8_t*)"RAW 20",6);assert(pipeline.command(selection));unsigned scansBoth=0,featuresBoth=0,rawBoth=0,bleFeatures=0,bleRaw=0;auto emit=[&](uint8_t kind,uint64_t stamp,const uint8_t*payload,uint16_t bytes,bool ble){if(kind!=KIND_SCAN){uint8_t framed[256];auto n=encodePacket(kind,dualSequence++,stamp,payload,bytes,framed);dualMode.write((char*)framed,n);}if(kind==KIND_SCAN)scansBoth++;if(kind==KIND_FEATURE){featuresBoth++;bleFeatures+=ble;assert(get16(payload+6)==80);}if(kind==KIND_SELECTED_RAW){rawBoth++;bleRaw+=ble;assert(get16(payload+4)==20&&get16(payload+8)==40);}};for(unsigned i=0;i<4000;i++){Capture sample{};sample.index=i;sample.stamp=uint64_t(i)*250;pipeline.add(sample,emit);}assert(scansBoth==4000&&featuresBoth==50&&rawBoth==100&&bleFeatures==0&&bleRaw==100);assert(pipeline.command(Command::parse((const uint8_t*)"FEATURES",8)));for(unsigned i=4000;i<4080;i++){Capture sample{};sample.index=i;sample.stamp=uint64_t(i)*250;pipeline.add(sample,emit);}assert(featuresBoth==51&&bleFeatures==1&&rawBoth==100);checks++;
 // Fault injection: neither owner may be bypassed, and each failed shutdown
 // operation must hold its phase until a successful retry, before deep sleep.
 for(unsigned failure=0;failure<=7;failure++){
  ShutdownSequence shutdown;FaultShutdownIO io;io.fail=failure;
  assert(!shutdown.step(false,false,io));assert(!shutdown.step(true,false,io));assert(!shutdown.step(false,true,io));assert(io.calls.empty());
  for(unsigned phase=1;phase<=7;phase++){
   if(phase==failure){for(unsigned retry=0;retry<3;retry++){assert(!shutdown.step(true,true,io));assert(unsigned(shutdown.phase)==phase&&io.calls.back()==phase);}io.fail=0;}
   assert(shutdown.step(true,true,io)==(phase==7));assert(io.calls.back()==phase);
  }
  auto calls=io.calls.size();assert(shutdown.step(true,true,io));assert(io.calls.size()==calls);checks++;
 }
 std::cout<<"{\"actual_core_cases\":"<<checks<<",\"scans\":4000,\"dynamic_samples\":80000,\"pressure_samples\":1000,\"feature_windows\":50,\"status\":\"pass\"}\n";
}
