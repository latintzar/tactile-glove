#pragma once
#include <stdint.h>
// Pure timing logic, shared by firmware and host-compiled behavioral tests.
namespace CuffButton {
enum Action { None, Wake, Pair, Sleep, Tap };
struct Control {
  bool boot=false, stable=false, raw=false, waitingRelease=false;
  uint32_t edge=0, down=0;
  void begin(bool wakeFromOff, uint32_t now) {
    boot=wakeFromOff; stable=raw=wakeFromOff; edge=down=now; waitingRelease=false;
  }
  Action tick(bool pressed, uint32_t now) {
    if (pressed!=raw) {raw=pressed;edge=now;}
    if (raw!=stable && uint32_t(now-edge)>=30) {
      stable=raw;
      if(stable) down=now;
      else {
        if(waitingRelease){waitingRelease=false;return None;}
        const uint32_t held=now-down;
        if(boot){boot=false;return held>=800 ? Wake:Sleep;}
        if(held<1500) return Tap;
      }
    }
    if(stable && !waitingRelease) {
      const uint32_t held=now-down;
      if(boot && held>=3000){boot=false;waitingRelease=true;return Pair;}
      if(!boot && held>=1500){waitingRelease=true;return Sleep;}
    }
    return None;
  }
};
}
