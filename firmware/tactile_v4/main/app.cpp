#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "app.hpp"
#include "storage.hpp"
#include "shutdown.hpp"
#include "http.hpp"
#include "esp_heap_caps.h"
#include <new>
#include "hardware.hpp"
#include "driver/gptimer.h"
#include "driver/ledc.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "driver/i2c.h"
#include "driver/spi_master.h"
#include "driver/sdspi_host.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_camera.h"
#include "esp_sleep.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_vfs_fat.h"
#include "lwip/sockets.h"
#include <cerrno>
#include <cstdio>
using namespace V4;
// Queue control stays internal; only foreground packet bytes use PSRAM.
// The acquisition ISR touches its separate internal-SRAM ring exclusively.
QueueHandle_t createPacketQueue(unsigned count){auto*control=(StaticQueue_t*)heap_caps_malloc(sizeof(StaticQueue_t),MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT);auto*storage=(uint8_t*)heap_caps_malloc(count*sizeof(Packet),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);if(!control||!storage){heap_caps_free(control);heap_caps_free(storage);return nullptr;}return xQueueCreateStatic(count,sizeof(Packet),storage,control);}
BaseType_t createCheckedTask(TaskFunction_t task,const char*name,uint32_t stack,void*argument,UBaseType_t priority,TaskHandle_t*handle,BaseType_t core){BaseType_t result=xTaskCreatePinnedToCore(task,name,stack,argument,priority,handle,core);ESP_ERROR_CHECK(result==pdPASS?ESP_OK:ESP_ERR_NO_MEM);return result;}
static Acquisition acquisition;static Adc adc;static SemaphoreHandle_t busMutex,packetMutex;
QueueHandle_t bleFrames,commands,usbFrames;
std::atomic<uint32_t> usbDrops{0},bleDrops{0};extern std::atomic<bool> usbMounted,usbSuspended;static QueueHandle_t wireFrames;
char wifiSsid[32]={},wifiPassword[33]={};
static std::atomic<uint32_t> packetSeq{0},blePacketSeq{0},wireDrops{0},cameraFrames{0},cameraDrops{0},imuOverruns{0};
static std::atomic<uint32_t> pairingUntil{0},lastImu[2]{};static std::atomic<bool> sleeping{false},adcBusy{false};
static CuffButton::Control powerButton;static uint32_t bootId;static gptimer_handle_t timer=nullptr;static std::atomic<bool> cameraStopped{false};static std::atomic<int> videoClient{-1};
// Frozen V4 two-expander power contract. RGB cathodes are active-low.
static ExpanderState expander;static std::atomic<uint32_t> controlFaults{0};
constexpr uint8_t EXPANDER=0x20,IMU=0x6B;
constexpr uint16_t CAM_IO=1<<0,CAM_ANALOG=1<<1,CAM_CORE=1<<2,CAM_IF=1<<3,CAM_RESET=1<<4,CAM_PWDN=1<<5;
constexpr uint16_t LED_R=1<<6,LED_G=1<<7,LED_B=1<<8,BAT_DIV=1<<9,REG_PFM=1<<10,USB_SET=1<<11,USB_CLR_N=1<<12,USB_SUSPEND=1<<13,CHG_DISABLE=1<<14,SD_EN=1<<15;
static std::atomic<uint16_t> batteryMv{0};static std::atomic<bool> lowBattery{false};
bool capturePowerQualified(){return acquisition.qualified.load()&&!sleeping.load();}
bool pairingAllowed(){return int32_t(pairingUntil.load()-uint32_t(esp_timer_get_time()/1000))>0;}
static bool readReg(uint8_t address,uint8_t reg,uint8_t*out,size_t n){return i2c_master_write_read_device(I2C_NUM_0,address,&reg,1,out,n,pdMS_TO_TICKS(10))==ESP_OK;}
static bool writeReg(uint8_t address,uint8_t reg,uint8_t value){uint8_t b[2]={reg,value};return i2c_master_write_to_device(I2C_NUM_0,address,b,2,pdMS_TO_TICKS(10))==ESP_OK;}
static bool output(uint16_t set,uint16_t clear){bool ok=expander.update(set,clear,[](uint16_t value){uint8_t b[3]={2,uint8_t(value),uint8_t(value>>8)};return i2c_master_write_to_device(I2C_NUM_0,EXPANDER,b,sizeof(b),pdMS_TO_TICKS(10))==ESP_OK;});if(!ok)controlFaults++;return ok;}
bool setSdPower(bool enabled){xSemaphoreTake(busMutex,portMAX_DELAY);bool ok=output(enabled?SD_EN:0,enabled?0:SD_EN);xSemaphoreGive(busMutex);return ok;}
static void queuePacket(uint8_t kind,uint64_t stamp,const uint8_t*p,uint16_t n,bool ble=false){
 xSemaphoreTake(packetMutex,portMAX_DELAY);Packet f{};f.size=encodePacket(kind,packetSeq.fetch_add(1),stamp,p,n,f.data);
 if(f.size){if(xQueueSend(wireFrames,&f,0)!=pdTRUE)wireDrops++;if(xQueueSend(usbFrames,&f,0)!=pdTRUE)usbDrops++;if(sdSensorFrames&&xQueueSend(sdSensorFrames,&f,0)!=pdTRUE)sdDrops++;
  queueBrowserPacket(kind,stamp,p,n);
  if(ble){f.size=encodePacket(kind,blePacketSeq.fetch_add(1),stamp,p,n,f.data);if(xQueueSend(bleFrames,&f,0)!=pdTRUE)bleDrops++;}}
 xSemaphoreGive(packetMutex);
}
static bool IRAM_ATTR tick(gptimer_handle_t t,const gptimer_alarm_event_data_t*e,void*){
 uint64_t stamp=esp_timer_get_time();acquisition.capture(stamp,uint32_t(e->alarm_value/250-1),adc);
 uint64_t count;gptimer_get_raw_count(t,&count);gptimer_alarm_config_t a{};a.alarm_count=(count/250+1)*250;gptimer_set_alarm_action(t,&a);return false;
}
static void acquisitionTask(void*){
 adc.begin();
 gptimer_config_t c{};c.clk_src=GPTIMER_CLK_SRC_DEFAULT;c.direction=GPTIMER_COUNT_UP;c.resolution_hz=1000000;c.intr_priority=3;
 ESP_ERROR_CHECK(gptimer_new_timer(&c,&timer));gptimer_event_callbacks_t cb{};cb.on_alarm=tick;ESP_ERROR_CHECK(gptimer_register_event_callbacks(timer,&cb,nullptr));
 gptimer_alarm_config_t a{};a.alarm_count=250;ESP_ERROR_CHECK(gptimer_set_alarm_action(timer,&a));ESP_ERROR_CHECK(gptimer_enable(timer));acquisition.enabled=true;ESP_ERROR_CHECK(gptimer_start(timer));
 for(;;){if(sleeping.load()){vTaskDelay(pdMS_TO_TICKS(20));continue;}if(acquisition.qualified.load()&&!acquisition.calibrated.load()){adcBusy=true;gpio_set_level(gpio_num_t(Pins::analogEnable),1);adc.begin();vTaskDelay(pdMS_TO_TICKS(700));if(acquisition.qualified.load()){bool ok=adc.recalibrate();acquisition.calibrated=ok&&acquisition.qualified.load()&&!sleeping.load();}adcBusy=false;}else if(!acquisition.qualified.load()){acquisition.calibrated=false;while(acquisition.active.load())vTaskDelay(1);adc.shutdown();gpio_set_level(gpio_num_t(Pins::analogEnable),0);}vTaskDelay(pdMS_TO_TICKS(100));}
}
static bool imuBegin(uint8_t IMU){uint8_t who=0;if(!readReg(IMU,0x0F,&who,1)||who!=0x6B)return false;
 if(!writeReg(IMU,0x12,0x01)){return false;}
 for(unsigned i=0;i<20;i++){vTaskDelay(pdMS_TO_TICKS(2));uint8_t v;if(!readReg(IMU,0x12,&v,1))return false;if(!(v&1))break;if(i==19)return false;}
 // Both sources: +/-4g, +/-1000dps, 833Hz; timestamp every8 FIFOslots.
 if(!writeReg(IMU,0x12,0x44)||!writeReg(IMU,0x10,0x78)||!writeReg(IMU,0x11,0x78)||!writeReg(IMU,0x19,0x20)||!writeReg(IMU,0x42,0xAA))return false;
 // AN5398 section 6.4: after the TIMESTAMP2 reset command, wait 150 us
 // before writing any other device register.
 esp_rom_delay_us(150);
 return writeReg(IMU,0x07,24)&&writeReg(IMU,0x08,0)&&writeReg(IMU,0x09,0x77)&&writeReg(IMU,0x0A,0x86);
}
static void imuTask(void*){bool ready[2]={},needTimestamp[2]={true,true};uint64_t retry[2]={};
 for(;;){if(sleeping.load()||!acquisition.qualified.load()){vTaskDelay(pdMS_TO_TICKS(10));continue;}
  for(uint8_t source=0;source<2;source++){const uint8_t address=source?0x6B:0x6A;if(!ready[source]&&uint64_t(esp_timer_get_time())<retry[source])continue;
   xSemaphoreTake(busMutex,portMAX_DELAY);if(!ready[source]){ready[source]=imuBegin(address);needTimestamp[source]=true;}
   uint8_t st[2]={},time[4]={},words[28*7];uint8_t count=0;uint16_t flags=4;ImuAnchor a;
   if(ready[source]&&readReg(address,0x3A,st,2)){
    FifoStatus fifo=FifoStatus::decode(st[0],st[1]);
    if(fifo.overrun||fifo.invalid){flags|=1;imuOverruns.fetch_add(1);needTimestamp[source]=true;ready[source]=writeReg(address,0x0A,0)&&writeReg(address,0x0A,0x86);fifo.count=0;}

    uint64_t before=esp_timer_get_time();bool ok=ready[source]&&readReg(address,0x40,time,4);uint64_t after=esp_timer_get_time();
    ok=ok&&a.set(get32(time),before,after);unsigned remaining=std::min<unsigned>(28,fifo.count);
    // AN5398 section4.7.1: FIFO register address wraps7E->78 for a burst.
    ok=ok&&(!remaining||readReg(address,0x78,words,remaining*7));
    for(unsigned i=0;ok&&i<remaining;i++){uint8_t*w=words+7*i;uint8_t tag=w[0]>>3;if(needTimestamp[source]&&tag!=4)continue;if(tag==4)needTimestamp[source]=false;if(i!=count)memmove(words+7*count,w,7);count++;}
    if(needTimestamp[source])flags|=2;
    if(ok&&(count||(flags&1))){uint8_t p[220];uint16_t n=imuPayload(p,a,flags,words,count,source);queuePacket(KIND_IMU_FIFO,a.midpointUs,p,n);if(count)lastImu[source].store(after);}else if(!ok)ready[source]=false;
   }else ready[source]=false;
   if(!ready[source]){retry[source]=esp_timer_get_time()+1000000;}
   xSemaphoreGive(busMutex);vTaskDelay(1);
  }vTaskDelay(pdMS_TO_TICKS(2));
 }
}
static void pipelineTask(void*){LabelState label;uint64_t nextLabel=0;CapturePackets packets;Capture c{};
 for(;;){uint8_t cmd[32];while(xQueueReceive(commands,cmd,0)==pdTRUE){Command parsed=Command::parse(cmd+1,cmd[0]);if(packets.command(parsed))continue;if(label.apply(parsed)){uint8_t value[13];label.payload(value);queuePacket(KIND_LABEL,esp_timer_get_time(),value,13,true);nextLabel=esp_timer_get_time()+1000000;}}
  uint64_t now=esp_timer_get_time();if(now>=nextLabel){uint8_t value[13];label.payload(value);queuePacket(KIND_LABEL,now,value,13,true);nextLabel=now+1000000;}if(!acquisition.ring.pop(c)){vTaskDelay(1);continue;}
  if(uint32_t(c.stamp)-lastImu[0].load()>100000||uint32_t(c.stamp)-lastImu[1].load()>100000)c.flags|=FLAG_IMU_STALE;
  packets.add(c,queuePacket);
 }
}
static int listener(unsigned port){int s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);if(s<0)return -1;int yes=1;setsockopt(s,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes));sockaddr_in a{};a.sin_family=AF_INET;a.sin_port=htons(port);a.sin_addr.s_addr=htonl(INADDR_ANY);if(bind(s,(sockaddr*)&a,sizeof(a))<0||listen(s,1)<0){close(s);return -1;}return s;}
static bool sendAll(int s,const uint8_t*p,size_t n){uint64_t deadline=esp_timer_get_time()+200000;while(n){int r=send(s,p,n,MSG_DONTWAIT);if(r>0){p+=r;n-=r;}else if(r<0&&(errno==EAGAIN||errno==EWOULDBLOCK)){if(uint64_t(esp_timer_get_time())>=deadline)return false;vTaskDelay(1);}else return false;}return true;}
static void tactileNetwork(void*){int server=listener(7002);if(server<0)vTaskDelete(nullptr);for(;;){int c=accept(server,nullptr,nullptr);if(c<0){vTaskDelay(20);continue;}Packet p;while(xQueueReceive(wireFrames,&p,pdMS_TO_TICKS(1000))!=pdTRUE){};do {if(!sendAll(c,p.data,p.size)){wireDrops.fetch_add(1);break;}}while(xQueueReceive(wireFrames,&p,pdMS_TO_TICKS(1000))==pdTRUE);shutdown(c,SHUT_RDWR);close(c);}}
static bool cameraBegin(){
 xSemaphoreTake(busMutex,portMAX_DELAY);
 bool ok=output(CAM_PWDN, CAM_IO|CAM_ANALOG|CAM_CORE|CAM_IF|CAM_RESET);
 ok=ok&&output(CAM_IO,0);vTaskDelay(pdMS_TO_TICKS(20));ok=ok&&output(CAM_ANALOG,0);vTaskDelay(pdMS_TO_TICKS(20));ok=ok&&output(CAM_CORE,0);vTaskDelay(pdMS_TO_TICKS(20));ok=ok&&output(CAM_IF,0);
 ledc_timer_config_t lt{};lt.speed_mode=LEDC_LOW_SPEED_MODE;lt.timer_num=LEDC_TIMER_0;lt.duty_resolution=LEDC_TIMER_1_BIT;lt.freq_hz=24000000;lt.clk_cfg=LEDC_AUTO_CLK;ok=ok&&ledc_timer_config(&lt)==ESP_OK;ledc_channel_config_t lc{};lc.gpio_num=15;lc.speed_mode=LEDC_LOW_SPEED_MODE;lc.channel=LEDC_CHANNEL_0;lc.timer_sel=LEDC_TIMER_0;lc.duty=1;ok=ok&&ledc_channel_config(&lc)==ESP_OK;vTaskDelay(pdMS_TO_TICKS(1));ok=ok&&output(0,CAM_PWDN);vTaskDelay(pdMS_TO_TICKS(2));ok=ok&&output(CAM_RESET,0);vTaskDelay(pdMS_TO_TICKS(26));
 camera_config_t c{};c.pin_pwdn=-1;c.pin_reset=-1;c.pin_xclk=15;c.pin_sccb_sda=-1;c.pin_sccb_scl=-1;c.sccb_i2c_port=0;c.pin_d0=11;c.pin_d1=9;c.pin_d2=8;c.pin_d3=10;c.pin_d4=12;c.pin_d5=18;c.pin_d6=17;c.pin_d7=16;c.pin_vsync=6;c.pin_href=7;c.pin_pclk=13;c.xclk_freq_hz=24000000;c.ledc_timer=LEDC_TIMER_0;c.ledc_channel=LEDC_CHANNEL_0;c.pixel_format=PIXFORMAT_JPEG;c.frame_size=FRAMESIZE_VGA;c.jpeg_quality=12;c.fb_count=2;c.fb_location=CAMERA_FB_IN_PSRAM;c.grab_mode=CAMERA_GRAB_WHEN_EMPTY;
 ok=ok&&esp_camera_init(&c)==ESP_OK;if(ok){sensor_t*s=esp_camera_sensor_get();ok=s&&s->id.PID==OV5640_PID;if(ok)ok=configureCameraTiming([&](unsigned reg,unsigned mask){return s->get_reg(s,reg,mask);},[&](unsigned reg,unsigned mask,unsigned value){return s->set_reg(s,reg,mask,value);});if(!ok){output(CAM_PWDN,CAM_RESET);esp_camera_deinit();}}
 xSemaphoreGive(busMutex);return ok;
}
static void cameraPowerOff(){xSemaphoreTake(busMutex,portMAX_DELAY);output(CAM_PWDN,CAM_RESET);ledc_stop(LEDC_LOW_SPEED_MODE,LEDC_CHANNEL_0,0);output(0,CAM_IF);output(0,CAM_CORE);vTaskDelay(pdMS_TO_TICKS(20));output(0,CAM_ANALOG);vTaskDelay(pdMS_TO_TICKS(20));output(0,CAM_IO);xSemaphoreGive(busMutex);}
static void cameraCapture(void*){CameraPacer pacer;unsigned startupFrames=2;
 while(!acquisition.qualified.load()&&!sleeping.load())vTaskDelay(pdMS_TO_TICKS(20));
 if(sleeping.load()||!cameraBegin()){cameraPowerOff();cameraDrops++;cameraStopped=true;vTaskDelete(nullptr);}
 while(!sleeping.load()){
  camera_fb_t*fb=esp_camera_fb_get();if(!fb){cameraDrops++;vTaskDelay(1);continue;}
  uint64_t stamp=uint64_t(fb->timestamp.tv_sec)*1000000+fb->timestamp.tv_usec;uint32_t seq=cameraFrames.fetch_add(1);if(startupFrames){startupFrames--;cameraDrops++;esp_camera_fb_return(fb);continue;}if(!pacer.accept(stamp)){cameraDrops++;esp_camera_fb_return(fb);continue;}
  bool valid=fb->format==PIXFORMAT_JPEG&&fb->len>4&&fb->len<=524288&&fb->buf[0]==0xFF&&fb->buf[1]==0xD8;
  VideoFrame*f=valid?new(std::nothrow) VideoFrame:nullptr;
  if(f){f->bytes=32+fb->len;f->storage=(uint8_t*)heap_caps_malloc(f->bytes+1,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);f->data=f->storage?f->storage+1:nullptr;if(f->storage)f->storage[0]=1;if(!f->data){delete f;f=nullptr;}}
  if(f){jpegHeader(f->data,seq,stamp,fb->len,crc32(fb->buf,fb->len),fb->width,fb->height);memcpy(f->data+32,fb->buf,fb->len);}
  esp_camera_fb_return(fb);
  if(f){publishBrowserVideo(f);f->refs++;if(xQueueSend(videoFrames,&f,0)!=pdTRUE){cameraDrops++;releaseVideo(f);}f->refs++;if(xQueueSend(sdVideoFrames,&f,0)!=pdTRUE){sdDrops++;releaseVideo(f);}releaseVideo(f);}else cameraDrops++;
 }
 // The owner has returned its final frame. Assert sensor reset/PWDN before
 // esp_camera_deinit stops XCLK; an I2C failure must retain the powered state.
 for(;;){bool reset=false;if(xSemaphoreTake(busMutex,pdMS_TO_TICKS(100))==pdTRUE){reset=output(CAM_PWDN,CAM_RESET);xSemaphoreGive(busMutex);}if(reset)break;vTaskDelay(pdMS_TO_TICKS(20));}
 xSemaphoreTake(busMutex,portMAX_DELAY);esp_err_t deinit=esp_camera_deinit();xSemaphoreGive(busMutex);
 if(deinit!=ESP_OK){controlFaults++;for(;;)vTaskDelay(pdMS_TO_TICKS(100));}
 cameraStopped=true;vTaskDelete(nullptr);
}
static void cameraNetwork(void*){int server=listener(7001);if(server<0)vTaskDelete(nullptr);
 for(;;){int c=accept(server,nullptr,nullptr);if(c<0){vTaskDelay(20);continue;}videoClient=c;VideoFrame*old=nullptr;while(xQueueReceive(videoFrames,&old,0)==pdTRUE){releaseVideo(old);cameraDrops++;}
  while(!sleeping.load()){VideoFrame*f=nullptr;if(xQueueReceive(videoFrames,&f,pdMS_TO_TICKS(1000))!=pdTRUE)continue;bool ok=sendAll(c,f->data,f->bytes);releaseVideo(f);if(!ok){cameraDrops++;break;}}
  videoClient=-1;shutdown(c,SHUT_RDWR);close(c);
 }
}
static void wifiBegin(){ESP_ERROR_CHECK(esp_netif_init());ESP_ERROR_CHECK(esp_event_loop_create_default());esp_netif_create_default_wifi_ap();wifi_init_config_t init=WIFI_INIT_CONFIG_DEFAULT();ESP_ERROR_CHECK(esp_wifi_init(&init));nvs_handle_t n;ESP_ERROR_CHECK(nvs_open("v4",NVS_READWRITE,&n));size_t len=sizeof(wifiPassword);if(nvs_get_str(n,"wifi_key",wifiPassword,&len)!=ESP_OK){static const char chars[]="ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";for(unsigned i=0;i<20;i++)wifiPassword[i]=chars[esp_random()%(sizeof(chars)-1)];ESP_ERROR_CHECK(nvs_set_str(n,"wifi_key",wifiPassword));ESP_ERROR_CHECK(nvs_commit(n));}nvs_close(n);uint8_t mac[6];ESP_ERROR_CHECK(esp_wifi_get_mac(WIFI_IF_AP,mac));snprintf(wifiSsid,sizeof(wifiSsid),"Artisan-%02X%02X%02X",mac[3],mac[4],mac[5]);wifi_config_t cfg{};strncpy((char*)cfg.ap.ssid,wifiSsid,sizeof(cfg.ap.ssid));strncpy((char*)cfg.ap.password,wifiPassword,sizeof(cfg.ap.password));cfg.ap.ssid_len=strlen(wifiSsid);cfg.ap.channel=1;cfg.ap.max_connection=1;cfg.ap.authmode=WIFI_AUTH_WPA2_PSK;ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP,&cfg));ESP_ERROR_CHECK(esp_wifi_start());}
static void networkStart(void*){while(!capturePowerQualified()&&!sleeping.load())vTaskDelay(pdMS_TO_TICKS(20));if(!sleeping.load()){wifiBegin();beginBrowser();createCheckedTask(tactileNetwork,"tactile-wifi",4096,nullptr,8,nullptr,0);createCheckedTask(cameraNetwork,"camera-wifi",6144,nullptr,7,nullptr,0);}vTaskDelete(nullptr);}
struct ShutdownIO {
 bool stopImus(){for(uint8_t address:{0x6A,0x6B})if(!writeReg(address,0x10,0)||!writeReg(address,0x11,0)||!writeReg(address,0x0A,0))return false;return true;}
 bool resetCamera(){return output(CAM_PWDN,CAM_RESET);}
 bool stopClock(){auto result=ledc_stop(LEDC_LOW_SPEED_MODE,LEDC_CHANNEL_0,0);if(result!=ESP_OK&&result!=ESP_ERR_INVALID_STATE)return false;return gpio_reset_pin(gpio_num_t(15))==ESP_OK&&gpio_set_level(gpio_num_t(15),0)==ESP_OK&&gpio_set_direction(gpio_num_t(15),GPIO_MODE_OUTPUT)==ESP_OK;}
 bool disableInterface(){return output(0,CAM_IF);}
 bool disableCore(){if(!output(0,CAM_CORE))return false;vTaskDelay(pdMS_TO_TICKS(20));return true;}
 bool disableAnalog(){if(!output(0,CAM_ANALOG))return false;vTaskDelay(pdMS_TO_TICKS(20));return true;}
 bool disableFinalRails(){return output(LED_R|LED_G|LED_B|REG_PFM,CAM_IO|BAT_DIV|USB_SET|USB_CLR_N|SD_EN);}
};
static void sleepNow(){
 sleeping=true;acquisition.enabled=false;if(timer)gptimer_stop(timer);
 // Keep rails applied while their peripheral owner is still active. A hard
 // driver/bus stall remains a hardware-reset release blocker, not permission
 // to cut power beneath DMA or to report successful deep sleep.
 int client=videoClient.load();if(client>=0)shutdown(client,SHUT_RDWR);
 while(acquisition.active.load()||adcBusy.load())vTaskDelay(1);
 acquisition.calibrated=false;adc.shutdown();gpio_set_level(gpio_num_t(Pins::analogEnable),0);
 ShutdownSequence sequence;ShutdownIO io;
 for(;;){
  if(cameraStopped.load())stopStorage(); // drain the final camera frame before SD teardown
  bool done=false;
  if(cameraStopped.load()&&sdStopped.load()&&xSemaphoreTake(busMutex,pdMS_TO_TICKS(100))==pdTRUE){
   done=sequence.step(cameraStopped.load(),sdStopped.load(),io);xSemaphoreGive(busMutex);
  }
  if(done)break;
  vTaskDelay(pdMS_TO_TICKS(20));
 }
 while(!gpio_get_level(gpio_num_t(Pins::button)))vTaskDelay(pdMS_TO_TICKS(20));
 ESP_ERROR_CHECK(esp_sleep_enable_ext0_wakeup(gpio_num_t(Pins::button),0));esp_deep_sleep_start();
}
static std::atomic<bool> powerStop{false};
static void powerTask(void*){
 adc_oneshot_unit_handle_t unit;adc_oneshot_unit_init_cfg_t u{};u.unit_id=ADC_UNIT_1;ESP_ERROR_CHECK(adc_oneshot_new_unit(&u,&unit));adc_oneshot_chan_cfg_t channel{};channel.atten=ADC_ATTEN_DB_12;channel.bitwidth=ADC_BITWIDTH_DEFAULT;ESP_ERROR_CHECK(adc_oneshot_config_channel(unit,ADC_CHANNEL_0,&channel));adc_cali_handle_t cal=nullptr;adc_cali_curve_fitting_config_t cfg{};cfg.unit_id=ADC_UNIT_1;cfg.chan=ADC_CHANNEL_0;cfg.atten=ADC_ATTEN_DB_12;cfg.bitwidth=ADC_BITWIDTH_DEFAULT;bool calibrationOk=adc_cali_create_scheme_curve_fitting(&cfg,&cal)==ESP_OK;PowerGate gate;
 for(;;){if(sleeping.load()){vTaskDelay(pdMS_TO_TICKS(100));continue;}xSemaphoreTake(busMutex,portMAX_DELAY);bool divider=output(BAT_DIV,0);xSemaphoreGive(busMutex);vTaskDelay(pdMS_TO_TICKS(50));int total=0;bool ok=divider&&calibrationOk;for(unsigned i=0;i<8&&ok;i++){int raw,mv;ok=adc_oneshot_read(unit,ADC_CHANNEL_0,&raw)==ESP_OK&&adc_cali_raw_to_voltage(cal,raw,&mv)==ESP_OK;if(ok)total+=mv;}
  batteryMv=ok?uint16_t(total/4):0;lowBattery=batteryMv<3400;uint8_t status=0xFF;xSemaphoreTake(busMutex,portMAX_DELAY);bool statusOk=readReg(0x21,0,&status,1);xSemaphoreGive(busMutex);
  bool usbGood=highCurrentUsb(status,statusOk);
  bool qualified=gate.update(batteryMv,ok,usbGood);lowBattery=batteryMv>500&&batteryMv<3400;
  if(gate.stopRequested)powerStop=true;
  acquisition.qualified=qualified;vTaskDelay(pdMS_TO_TICKS(950));
 }
}
static void controlsTask(void*){uint64_t next=0;bool usbWas=false,usbSuspendWas=false;uint32_t ledPhase=~0u;for(;;){uint64_t now=esp_timer_get_time();if(powerStop.load())sleepNow();auto a=powerButton.tick(!gpio_get_level(gpio_num_t(Pins::button)),now/1000);if(a==CuffButton::Sleep)sleepNow();if(a==CuffButton::Tap)acquisition.enabled=!acquisition.enabled.load();bool configured=usbMounted.load()&&!usbSuspended.load();
 xSemaphoreTake(busMutex,portMAX_DELAY);uint8_t status=0xFF;bool statusOk=readReg(0x21,0,&status,1);xSemaphoreGive(busMutex);updateUsbVbus(statusOk&&!(status&(1<<3)));configured=usbMounted.load()&&!usbSuspended.load();
 bool suspended=usbSuspended.load();if(configured!=usbWas||suspended!=usbSuspendWas){xSemaphoreTake(busMutex,portMAX_DELAY);bool ok;if(configured){ok=output(USB_CLR_N,USB_SUSPEND|USB_SET)&&output(USB_SET,0)&&output(0,USB_SET);if(!ok)output(0,USB_SET|USB_CLR_N);}else ok=output(usbSuspended?USB_SUSPEND:0,USB_SET|USB_CLR_N|(usbSuspended?0:USB_SUSPEND));xSemaphoreGive(busMutex);if(ok){usbWas=configured;usbSuspendWas=suspended;}}
 uint32_t phase=now/100000;if(phase!=ledPhase){ledPhase=phase;uint16_t on=0;if(pairingAllowed())on=(phase%10<5)?LED_B:0;else if(lowBattery||!acquisition.qualified.load()||!acquisition.calibrated.load())on=LED_R|LED_G;else if(controlFaults.load()||acquisition.faults.load()||cameraStopped.load()||(!sdMounted.load()&&videoClient.load()<0))on=(phase%10<2||phase%10==3)?LED_R:0;else on=acquisition.enabled.load()?LED_G:(phase%20<2?LED_G:0);xSemaphoreTake(busMutex,portMAX_DELAY);output((LED_R|LED_G|LED_B)&~on,on);xSemaphoreGive(busMutex);}
 if(now>=next){uint8_t p[42]{};put32(p,acquisition.late.load());put32(p+4,acquisition.faults.load());put32(p+8,wireDrops.load()+usbDrops.load()+acquisition.drops.load());put32(p+12,lastImu[0].load()&&lastImu[1].load()?0x6B:0);put32(p+20,acquisition.maxUs.load());put32(p+24,bleDrops.load());put32(p+28,acquisition.drops.load());put16(p+32,batteryMv);put16(p+34,(!acquisition.enabled?1:0)|(pairingAllowed()?2:0)|(!acquisition.qualified?4:0));put16(p+36,3000);put16(p+38,1250);put16(p+40,2500);queuePacket(KIND_HEALTH,now,p,42,true);uint8_t v[32]{};put32(v,bootId);put32(v+4,cameraFrames.load());put32(v+8,cameraDrops.load());put32(v+12,imuOverruns.load());put32(v+16,833);put32(v+20,acquisition.drops.load());put32(v+24,sdDrops.load());put32(v+28,(sdMounted.load()?1:0)|(cameraStopped.load()?2:0)|(uint32_t(now)-lastImu[0].load()>100000?4:0)|(uint32_t(now)-lastImu[1].load()>100000?8:0)|(controlFaults.load()?16:0));queuePacket(KIND_V4_STATUS,now,v,32,true);uint8_t browser[8];browserStatus(browser);queuePacket(KIND_BROWSER_STATUS,now,browser,8);next=now+1000000;}vTaskDelay(pdMS_TO_TICKS(10));}}
extern "C" void app_main(){
 ESP_ERROR_CHECK(nvs_flash_init());bootId=esp_random();gpio_set_level(gpio_num_t(Pins::analogEnable),0);gpio_set_direction(gpio_num_t(Pins::analogEnable),GPIO_MODE_OUTPUT);gpio_set_direction(gpio_num_t(Pins::button),GPIO_MODE_INPUT);gpio_pullup_en(gpio_num_t(Pins::button));
 // A wake is validated before enabling analog/camera loads.
 powerButton.begin(esp_sleep_get_wakeup_cause()==ESP_SLEEP_WAKEUP_EXT0,esp_timer_get_time()/1000);if(powerButton.boot){for(;;){auto a=powerButton.tick(!gpio_get_level(gpio_num_t(Pins::button)),esp_timer_get_time()/1000);if(a==CuffButton::Sleep){esp_sleep_enable_ext0_wakeup(gpio_num_t(Pins::button),0);esp_deep_sleep_start();}if(a==CuffButton::Pair){pairingUntil=uint32_t(esp_timer_get_time()/1000)+120000;break;}if(a==CuffButton::Wake)break;vTaskDelay(pdMS_TO_TICKS(10));}}
 busMutex=xSemaphoreCreateMutex();packetMutex=xSemaphoreCreateMutex();wireFrames=createPacketQueue(128);bleFrames=createPacketQueue(16);commands=xQueueCreate(8,32);usbFrames=createPacketQueue(128);assert(busMutex&&packetMutex&&wireFrames&&bleFrames&&commands&&usbFrames);
 i2c_config_t c{};c.mode=I2C_MODE_MASTER;c.sda_io_num=Pins::sda;c.scl_io_num=Pins::scl;c.sda_pullup_en=GPIO_PULLUP_ENABLE;c.scl_pullup_en=GPIO_PULLUP_ENABLE;c.master.clk_speed=400000;ESP_ERROR_CHECK(i2c_param_config(I2C_NUM_0,&c));ESP_ERROR_CHECK(i2c_driver_install(I2C_NUM_0,c.mode,0,0,0));
 // Fail closed until the V4 power-board contract is compiled in and qualified.
 expander.confirmed=CAM_PWDN|LED_R|LED_G|LED_B;
 ESP_ERROR_CHECK(writeReg(EXPANDER,2,expander.confirmed&255)?ESP_OK:ESP_FAIL);ESP_ERROR_CHECK(writeReg(EXPANDER,3,expander.confirmed>>8)?ESP_OK:ESP_FAIL);ESP_ERROR_CHECK(writeReg(EXPANDER,6,0)?ESP_OK:ESP_FAIL);ESP_ERROR_CHECK(writeReg(EXPANDER,7,0)?ESP_OK:ESP_FAIL);
 beginStorage(bootId);beginUsb();beginBle();output(0,REG_PFM);acquisition.qualified=false;
 createCheckedTask(acquisitionTask,"capture-init",4096,nullptr,20,nullptr,1);createCheckedTask(pipelineTask,"tactile-pack",6144,nullptr,12,nullptr,0);createCheckedTask(imuTask,"ism330dhcx",4096,nullptr,13,nullptr,0);createCheckedTask(networkStart,"network-start",6144,nullptr,7,nullptr,0);createCheckedTask(cameraCapture,"camera-capture",6144,nullptr,9,nullptr,0);createCheckedTask(controlsTask,"button-health",4096,nullptr,6,nullptr,0);createCheckedTask(powerTask,"battery",4096,nullptr,5,nullptr,0);
}
