#pragma once
#include <stdint.h>

namespace CuffDma {
// Stop before releasing DMA ownership. A failed stop latches the peripheral off;
// caller-owned static DMA storage also stays valid through a hardware fault.
template <typename Peripheral, typename Clock>
bool abort(Peripheral *spi, Clock now, uint32_t timeoutUs=100) {
  spi->EVENTS_STOPPED=0;
  spi->TASKS_STOP=1;
  const uint32_t started=now();
  uint32_t polls=4096;
  while(!spi->EVENTS_STOPPED && uint32_t(now()-started)<timeoutUs && --polls) {}
  const bool stopped=spi->EVENTS_STOPPED!=0;
  spi->ENABLE=0;
  __DSB();
  spi->TXD.MAXCNT=0;spi->RXD.MAXCNT=0;
  spi->TXD.PTR=0;spi->RXD.PTR=0;
  __DMB();
  return stopped;
}
}
