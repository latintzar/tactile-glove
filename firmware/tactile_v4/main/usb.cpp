#include "app.hpp"
#include "core.hpp"
#include "freertos/task.h"
#include "tinyusb.h"
#include "tusb_cdc_acm.h"
#include "tusb.h"
#include "esp_timer.h"
#include <atomic>
std::atomic<bool> usbMounted{false},usbSuspended{false};static std::atomic<uint32_t> usbEpoch{0};
extern QueueHandle_t usbFrames;
extern std::atomic<uint32_t> usbDrops;
extern "C" void tud_mount_cb(){usbEpoch++;usbMounted=true;usbSuspended=false;}
extern "C" void tud_umount_cb(){usbEpoch++;usbMounted=false;usbSuspended=false;}
extern "C" void tud_suspend_cb(bool){usbSuspended=true;}
extern "C" void tud_resume_cb(){usbSuspended=false;}
static bool vbusPresent=false;
void updateUsbVbus(bool present){if(present==vbusPresent)return;vbusPresent=present;if(present)tud_connect();else{tud_disconnect();usbEpoch++;usbMounted=false;usbSuspended=false;}}
static void usbRx(int,cdcacm_event_t*){static V4::CommandLine line;static uint32_t generation=0;uint32_t epoch=usbEpoch.load();if(epoch!=generation){line.reset();generation=epoch;}uint8_t bytes[64],command[32]{};size_t count=0;while(tinyusb_cdcacm_read(TINYUSB_CDC_ACM_0,bytes,sizeof(bytes),&count)==ESP_OK&&count){if(!usbMounted.load()||usbSuspended.load()){line.reset();continue;}for(size_t i=0;i<count;i++)if(line.feed(bytes[i],command))xQueueSend(commands,command,0);}}
static uint8_t configuration[]={TUD_CONFIG_DESCRIPTOR(1,2,0,TUD_CONFIG_DESC_LEN+TUD_CDC_DESC_LEN,0,500),TUD_CDC_DESCRIPTOR(0,0,0x81,8,0x02,0x82,64)};
static void usbTask(void*){Packet p{};bool delimiter=true;for(;;){if(xQueueReceive(usbFrames,&p,pdMS_TO_TICKS(100))!=pdTRUE)continue;if(!usbMounted||usbSuspended){usbDrops++;delimiter=true;continue;}size_t at=0;uint64_t deadline=esp_timer_get_time()+20000;while(at<p.size){uint8_t z=0;size_t n=tinyusb_cdcacm_write_queue(TINYUSB_CDC_ACM_0,delimiter?&z:p.data+at,delimiter?1:p.size-at);if(delimiter){if(n)delimiter=false;}else at+=n;tinyusb_cdcacm_write_flush(TINYUSB_CDC_ACM_0,0);if(uint64_t(esp_timer_get_time())>=deadline||!usbMounted||usbSuspended){usbDrops++;delimiter=true;break;}if(!n)vTaskDelay(1);}}}
void beginUsb(){tinyusb_config_t cfg{};cfg.configuration_descriptor=configuration;ESP_ERROR_CHECK(tinyusb_driver_install(&cfg));tud_disconnect();tinyusb_config_cdcacm_t c{};c.usb_dev=TINYUSB_USBDEV_0;c.cdc_port=TINYUSB_CDC_ACM_0;c.callback_rx=usbRx;ESP_ERROR_CHECK(tusb_cdc_acm_init(&c));createCheckedTask(usbTask,"usb-frames",4096,nullptr,8,nullptr,0);}
