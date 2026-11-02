#pragma once
#include "esp_attr.h"
#include "core.hpp"
#include "driver/gpio.h"
#include "esp_rom_gpio.h"
#include "esp_rom_sys.h"
#include "esp_private/periph_ctrl.h"
#include "soc/gpio_sig_map.h"
#include "soc/spi_struct.h"
#include "hal/spi_ll.h"
#include "hal/gpio_ll.h"
#include "esp_timer.h"
namespace V4 {
struct Adc {
 bool ready=false;
 static uint64_t IRAM_ATTR now(){return esp_timer_get_time();}
 static void IRAM_ATTR pin(int p,int v){gpio_ll_set_level(&GPIO,p,v);}
 static void IRAM_ATTR delayNs125(){for(unsigned i=0;i<30;i++)asm volatile("nop");}
 void begin(){
  for(int p:{Pins::adcClock,Pins::adcCnv,Pins::muxClock,Pins::muxData,Pins::muxLatch}){gpio_reset_pin(gpio_num_t(p));gpio_set_direction(gpio_num_t(p),GPIO_MODE_OUTPUT);gpio_set_level(gpio_num_t(p),0);}
  gpio_set_direction(gpio_num_t(Pins::adcData),GPIO_MODE_INPUT);
  periph_module_enable(PERIPH_SPI2_MODULE);periph_module_reset(PERIPH_SPI2_MODULE);
  esp_rom_gpio_connect_out_signal(Pins::adcClock,FSPICLK_OUT_IDX,false,false);
  esp_rom_gpio_connect_in_signal(Pins::adcData,FSPIQ_IN_IDX,false);
  spi_ll_master_init(&GPSPI2);spi_ll_master_set_clock(&GPSPI2,80000000,16000000,128);
  spi_ll_master_set_mode(&GPSPI2,0);spi_ll_set_half_duplex(&GPSPI2,true);
  spi_ll_set_rx_lsbfirst(&GPSPI2,false);spi_ll_enable_mosi(&GPSPI2,false);spi_ll_enable_miso(&GPSPI2,true);spi_ll_master_select_cs(&GPSPI2,3);
  ready=true;
 }
 bool IRAM_ATTR transfer(unsigned bits,uint16_t& out){
  if(!ready || bits>512 || !bits)return false;
  spi_ll_set_miso_bitlen(&GPSPI2,bits);GPSPI2.dma_int_clr.val=~0u;
  GPSPI2.cmd.update=1;unsigned spins=2400;while(GPSPI2.cmd.update&&--spins){}
  if(!spins){ready=false;return false;}
  GPSPI2.cmd.usr=1;spins=24000;while(GPSPI2.cmd.usr&&--spins){}
  if(!spins){ready=false;return false;} // SPI2 permanently stops sampling; no DMA buffer involved.
  uint32_t v=GPSPI2.data_buf[0];out=uint16_t((v&255)<<8)|uint16_t((v>>8)&255);return true;
 }
 void IRAM_ATTR mux(unsigned bank,unsigned slot){
  uint8_t a=(slot&15)|((bank&3)<<4);
  for(int i=7;i>=0;i--){pin(Pins::muxData,(a>>i)&1);asm volatile("nop; nop;");pin(Pins::muxClock,1);asm volatile("nop; nop;");pin(Pins::muxClock,0);}
  pin(Pins::muxLatch,1);asm volatile("nop; nop;");pin(Pins::muxLatch,0);
 }
 bool IRAM_ATTR read(unsigned bank,unsigned slot,unsigned settle,uint16_t& value){
  value=0;if(!ready)return false;mux(bank,slot);esp_rom_delay_us(settle);
  pin(Pins::adcCnv,1);esp_rom_delay_us(1);pin(Pins::adcCnv,0);delayNs125();return transfer(16,value);
 }
 void shutdown(){ready=false;esp_rom_gpio_connect_out_signal(Pins::adcClock,SIG_GPIO_OUT_IDX,false,false);for(int p:{Pins::adcClock,Pins::adcCnv,Pins::muxClock,Pins::muxData,Pins::muxLatch})pin(p,0);periph_module_disable(PERIPH_SPI2_MODULE);}
 bool recalibrate(){
  // Board SDI is tied high. Exactly 1024 total clocks while CNV remains low.
  pin(Pins::adcCnv,1);esp_rom_delay_us(1);pin(Pins::adcCnv,0);delayNs125();uint16_t unused;
  bool ok=transfer(512,unused)&&transfer(512,unused);if(!ok)return false;
  vTaskDelay(pdMS_TO_TICKS(700));return true;
 }
};
}
