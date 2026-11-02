#pragma once
#include <cstddef>
#include <cstdint>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "packet.hpp"
extern QueueHandle_t bleFrames,commands;
extern char wifiSsid[32],wifiPassword[33];
extern bool pairingAllowed();
void beginBle();

void beginUsb();

void updateUsbVbus(bool present);

bool capturePowerQualified();

bool setSdPower(bool enabled);

QueueHandle_t createPacketQueue(unsigned count);
BaseType_t createCheckedTask(TaskFunction_t task,const char*name,uint32_t stack,void*argument,UBaseType_t priority,TaskHandle_t*handle,BaseType_t core);
