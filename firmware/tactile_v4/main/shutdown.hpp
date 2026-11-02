#pragma once
#include <cstdint>
namespace V4 {
// The workers own camera/DMA and SD/SPI teardown. This sequence may start only
// after both owners acknowledge. A failed operation never advances the phase.
struct ShutdownSequence {
 enum Phase : uint8_t { Workers, Imus, CameraReset, Clock, Interface, Core,
                        Analog, FinalRails, Complete };
 Phase phase=Workers;
 template<class IO> bool step(bool cameraIdle,bool storageIdle,IO& io) {
  if(!cameraIdle||!storageIdle)return false;
  if(phase==Workers)phase=Imus;
  bool ok=false;
  switch(phase){
   case Imus:ok=io.stopImus();break;
   case CameraReset:ok=io.resetCamera();break;
   case Clock:ok=io.stopClock();break;
   case Interface:ok=io.disableInterface();break;
   case Core:ok=io.disableCore();break;
   case Analog:ok=io.disableAnalog();break;
   case FinalRails:ok=io.disableFinalRails();break;
   case Complete:return true;
   default:return false;
  }
  if(ok)phase=Phase(unsigned(phase)+1);
  return phase==Complete;
 }
};
}
