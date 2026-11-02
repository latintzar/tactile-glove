#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>
// storage[0] is the browser prefix; data points at the unchanged GV4J record.
struct VideoFrame {std::atomic<unsigned> refs{1};size_t bytes;uint8_t*data;uint8_t*storage;};
