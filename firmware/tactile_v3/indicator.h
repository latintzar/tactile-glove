#pragma once
#include <stdint.h>
namespace CuffIndicator {
struct Color {uint8_t r,g,b;};
inline uint8_t breathe(uint32_t now,uint32_t period) {
 uint32_t p=now%period,half=period/2,x=(p<half?p:period-p)*1024/half;
 uint32_t eased=x*x*(3072-2*x)/(1024*1024);
 return uint8_t(8+72*eased/1024);
}
inline Color color(uint32_t now,bool boot,bool pairing,bool collecting,bool lowBattery,bool fault) {
 if(fault)return (now%1000<180 || (now%1000>=320 && now%1000<500))?Color{90,0,0}:Color{0,0,0};
 if(boot||pairing)return {0,0,breathe(now,1600)};
 if(lowBattery)return {70,22,0};
 return collecting?Color{0,breathe(now,2400),0}:Color{0,18,0};
}
}
