#pragma once
#include "app.hpp"
#include "video_frame.hpp"
extern QueueHandle_t videoFrames,sdVideoFrames,sdSensorFrames;
extern std::atomic<bool> sdMounted,sdStopped;
extern std::atomic<uint32_t> sdDrops;
void releaseVideo(VideoFrame*);
void beginStorage(uint32_t boot);
void stopStorage();

void holdSdPinsLow();
