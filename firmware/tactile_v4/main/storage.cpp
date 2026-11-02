#include "storage.hpp"
#include "core.hpp"
#include "freertos/task.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "driver/sdspi_host.h"
#include "esp_vfs_fat.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "sdmmc_cmd.h"
#include <cstdio>
#include <sys/stat.h>
#include <unistd.h>
#include <new>
QueueHandle_t videoFrames,sdVideoFrames,sdSensorFrames;
std::atomic<bool> sdMounted{false},sdStopped{false};std::atomic<uint32_t> sdDrops{0};static std::atomic<bool> stopping{false};static uint32_t bootId;
void releaseVideo(VideoFrame*f){if(f->refs.fetch_sub(1)==1){heap_caps_free(f->storage);delete f;}}
void holdSdPinsLow(){for(int pin:{V4::Pins::sdClock,V4::Pins::sdMosi,V4::Pins::sdCs}){gpio_reset_pin(gpio_num_t(pin));gpio_set_level(gpio_num_t(pin),0);gpio_set_direction(gpio_num_t(pin),GPIO_MODE_OUTPUT);}gpio_reset_pin(gpio_num_t(V4::Pins::sdMiso));gpio_set_direction(gpio_num_t(V4::Pins::sdMiso),GPIO_MODE_INPUT);}
static FILE* openPart(const char*kind,unsigned&part){char path[100];struct stat st;do{snprintf(path,sizeof(path),"/sd/%08lx-%03u.%s",(unsigned long)bootId,part++,kind);}while(stat(path,&st)==0);FILE*f=fopen(path,"wb");if(f)setvbuf(f,nullptr,_IOFBF,16384);return f;}
static void storage(void*){while(!capturePowerQualified()&&!stopping.load())vTaskDelay(pdMS_TO_TICKS(20));if(stopping.load()){sdStopped=true;vTaskDelete(nullptr);}sdmmc_host_t host=SDSPI_HOST_DEFAULT();host.slot=SPI3_HOST;host.max_freq_khz=20000;spi_bus_config_t bus{};bus.mosi_io_num=V4::Pins::sdMosi;bus.miso_io_num=V4::Pins::sdMiso;bus.sclk_io_num=V4::Pins::sdClock;bus.quadwp_io_num=-1;bus.quadhd_io_num=-1;bus.max_transfer_sz=16384;
 bool power=setSdPower(true);vTaskDelay(pdMS_TO_TICKS(5));bool busReady=power&&spi_bus_initialize(SPI3_HOST,&bus,SPI_DMA_CH_AUTO)==ESP_OK;bool ok=busReady;sdspi_device_config_t slot=SDSPI_DEVICE_CONFIG_DEFAULT();slot.host_id=SPI3_HOST;slot.gpio_cs=gpio_num_t(V4::Pins::sdCs);esp_vfs_fat_sdmmc_mount_config_t mount{};mount.max_files=4;mount.allocation_unit_size=16384;mount.format_if_mount_failed=false;sdmmc_card_t*card=nullptr;ok=ok&&esp_vfs_fat_sdspi_mount("/sd",&host,&slot,&mount,&card)==ESP_OK;
 bool teardownFailed=false;
 unsigned rawPart=0,videoPart=0;FILE*raw=ok?openPart("g3",rawPart):nullptr;FILE*video=ok?openPart("gv4j",videoPart):nullptr;ok=ok&&raw&&video;sdMounted=ok;uint64_t rawBytes=0,videoBytes=0,nextFlush=esp_timer_get_time()+1000000;
 for(;;){if(teardownFailed){vTaskDelay(pdMS_TO_TICKS(100));continue;}bool work=false;Packet p;for(unsigned n=0;n<64&&xQueueReceive(sdSensorFrames,&p,0)==pdTRUE;n++){work=true;if(ok){if(rawBytes+p.size>1000000000ULL){fclose(raw);raw=openPart("g3",rawPart);rawBytes=0;}if(!raw||fwrite(p.data,1,p.size,raw)!=p.size)ok=false;else rawBytes+=p.size;}if(!ok)sdDrops++;}
  VideoFrame*f=nullptr;if(xQueueReceive(sdVideoFrames,&f,0)==pdTRUE){work=true;if(ok){if(videoBytes+f->bytes>1000000000ULL){fclose(video);video=openPart("gv4j",videoPart);videoBytes=0;}if(!video||fwrite(f->data,1,f->bytes,video)!=f->bytes)ok=false;else videoBytes+=f->bytes;}if(!ok)sdDrops++;releaseVideo(f);}
  sdMounted=ok;if(uint64_t(esp_timer_get_time())>=nextFlush){if(ok&&(fflush(raw)||fflush(video)||fsync(fileno(raw))||fsync(fileno(video))))ok=false;nextFlush=esp_timer_get_time()+1000000;}
  if(stopping.load()&&!work){
   // This task alone owns the SD driver and pins. Keep power until unmount and
   // SPI release succeed; failed I2C power writes must not acknowledge off.
   if(raw){if(fclose(raw))sdDrops++;raw=nullptr;}if(video){if(fclose(video))sdDrops++;video=nullptr;}
   sdMounted=false;ok=false;
   if(card){if(esp_vfs_fat_sdcard_unmount("/sd",card)!=ESP_OK){sdDrops++;teardownFailed=true;continue;}card=nullptr;}
   if(busReady){if(spi_bus_free(SPI3_HOST)!=ESP_OK){sdDrops++;vTaskDelay(pdMS_TO_TICKS(100));continue;}busReady=false;}
   holdSdPinsLow();if(!setSdPower(false)){sdDrops++;vTaskDelay(pdMS_TO_TICKS(100));continue;}
   sdStopped=true;vTaskDelete(nullptr);
  }
  if(!work)vTaskDelay(1);
 }
}
void beginStorage(uint32_t boot){bootId=boot;videoFrames=xQueueCreate(2,sizeof(VideoFrame*));sdVideoFrames=xQueueCreate(2,sizeof(VideoFrame*));sdSensorFrames=createPacketQueue(128);assert(videoFrames&&sdVideoFrames&&sdSensorFrames);createCheckedTask(storage,"sd-writer",6144,nullptr,6,nullptr,0);}
void stopStorage(){stopping=true;}
