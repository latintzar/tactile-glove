#pragma once
#include <cstdint>
struct VideoFrame;
void beginBrowser();
// Called under the common packet producer mutex; never waits for the network.
void queueBrowserPacket(uint8_t kind,uint64_t stamp,const uint8_t*payload,uint16_t bytes);
void publishBrowserVideo(VideoFrame*frame);
// Eight-byte LE payload: packet drops, then JPEG drops; lifetime-of-boot totals.
void browserStatus(uint8_t payload[8]);
