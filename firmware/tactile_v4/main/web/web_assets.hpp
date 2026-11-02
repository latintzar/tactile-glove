#pragma once
#include <cstddef>
#include <cstdint>
struct WebAsset {const char* path;const char* mime;const uint8_t* data;size_t size;};
extern const WebAsset webAssets[];
extern const size_t webAssetCount;
