#!/usr/bin/env python3
"""Compile and run the exact reviewed cam_take body with deterministic RTOS stubs."""
from __future__ import annotations
import json, os, pathlib, re, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "camera_override" / "driver" / "cam_hal.c"
EXPECTED = "f81b24bee4eb3c1668a04bb90ae8b20c5d89396e3efede0fdc6a0280424ea700"

C_PREFIX = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef uint32_t TickType_t;
typedef int BaseType_t;
typedef void *QueueHandle_t;
#define pdTRUE 1
#define CONFIG_IDF_TARGET_ESP32S3 1
static const uint16_t JPEG_EOI_MARKER = 0xD9FF;

typedef struct {
    uint8_t *buf;
    size_t len;
    size_t width;
    size_t height;
    int format;
    struct { long tv_sec; long tv_usec; } timestamp;
} camera_fb_t;

typedef struct {
    QueueHandle_t frame_buffer_queue;
    uint8_t jpeg_mode;
    uint8_t psram_mode;
    int in_bytes_per_pixel;
    int fb_bytes_per_pixel;
} cam_obj_t;

static cam_obj_t *cam_obj;
static TickType_t now_tick;
static unsigned reset_count;
static unsigned give_count;
static unsigned receive_count;
struct event { camera_fb_t *fb; TickType_t advance; };
static struct event events[16];
static unsigned event_count, event_pos;

static TickType_t xTaskGetTickCount(void) { return now_tick; }
static BaseType_t xQueueReceive(QueueHandle_t q, void *out, TickType_t wait) {
    (void)q;
    receive_count++;
    if (event_pos >= event_count) {
        now_tick += wait;
        *(camera_fb_t **)out = NULL;
        return 0;
    }
    struct event e = events[event_pos++];
    now_tick += e.advance;
    *(camera_fb_t **)out = e.fb;
    return e.fb ? pdTRUE : 0;
}
static void ll_cam_dma_reset(cam_obj_t *obj) { (void)obj; reset_count++; }
static void cam_give(camera_fb_t *fb) { (void)fb; give_count++; }
static size_t ll_cam_memcpy(cam_obj_t *obj, uint8_t *d, const uint8_t *s, size_t n) {
    (void)obj; if (d != s) memmove(d, s, n); return n;
}
static int cam_verify_jpeg_eoi(const uint8_t *buf, uint32_t length) {
    if (!buf || length < 2) return -1;
    for (uint32_t i = length - 2; i > 0; --i)
        if (memcmp(buf + i, &JPEG_EOI_MARKER, 2) == 0) return (int)i;
    return (memcmp(buf, &JPEG_EOI_MARKER, 2) == 0) ? 0 : -1;
}
'''

C_SUFFIX = r'''
static uint8_t valid_bytes[] = {0x11, 0x22, 0xff, 0xd9, 0x33, 0x44};
static uint8_t short_bytes[] = {0xff};
static uint8_t bad_bytes[] = {0x10, 0x20, 0x30, 0x40};
static camera_fb_t valid_fb, short_fb, bad_fb, null_fb;
static cam_obj_t object;

#define CHECK(x, msg) do { if (!(x)) { fprintf(stderr, "%s:%d: %s\n", __func__, __LINE__, msg); return 0; } } while (0)
static void reset_case(void) {
    memset(&valid_fb, 0, sizeof(valid_fb)); valid_fb.buf = valid_bytes; valid_fb.len = sizeof(valid_bytes); valid_fb.width = 640; valid_fb.height = 480; valid_fb.format = 7; valid_fb.timestamp.tv_usec = 1234;
    memset(&short_fb, 0, sizeof(short_fb)); short_fb.buf = short_bytes; short_fb.len = sizeof(short_bytes);
    memset(&bad_fb, 0, sizeof(bad_fb)); bad_fb.buf = bad_bytes; bad_fb.len = sizeof(bad_bytes);
    memset(&null_fb, 0, sizeof(null_fb)); null_fb.buf = NULL; null_fb.len = 8;
    memset(&object, 0, sizeof(object)); object.frame_buffer_queue = (QueueHandle_t)1; object.jpeg_mode = 1;
    cam_obj = &object; now_tick = 0; reset_count = give_count = receive_count = event_count = event_pos = 0;
}
static void set_events(struct event *e, unsigned n) { memcpy(events, e, n * sizeof(*e)); event_count = n; }

static int test_valid(void) {
    reset_case(); struct event e[] = {{&valid_fb, 0}}; set_events(e, 1);
    camera_fb_t *got = cam_take(10);
    CHECK(got == &valid_fb, "valid frame not returned"); CHECK(got->len == 4, "EOI length not preserved");
    CHECK(got->width == 640 && got->height == 480 && got->timestamp.tv_usec == 1234, "frame metadata changed");
    CHECK(give_count == 0 && reset_count == 0 && receive_count == 1, "valid accounting"); return 1;
}
static int test_empty_retry(void) {
    reset_case(); camera_fb_t *got = cam_take(10);
    CHECK(got == NULL && reset_count == 1 && receive_count == 2, "empty GDMA retry accounting"); return 1;
}
static int test_retry_success(void) {
    reset_case(); struct event e[] = {{NULL, 2}, {&valid_fb, 0}}; set_events(e, 2);
    camera_fb_t *got = cam_take(10);
    CHECK(got == &valid_fb && reset_count == 1 && receive_count == 2, "retry did not use remaining budget"); return 1;
}
static int test_malformed_then_valid(void) {
    reset_case(); struct event e[] = {{&null_fb, 0}, {&valid_fb, 0}}; set_events(e, 2);
    camera_fb_t *got = cam_take(10);
    CHECK(got == &valid_fb && give_count == 1 && receive_count == 2, "malformed frame was not returned once"); return 1;
}
static int test_malformed_cap(void) {
    reset_case(); struct event e[] = {{&bad_fb, 0}, {&short_fb, 0}, {&null_fb, 0}, {&valid_fb, 0}}; set_events(e, 4);
    camera_fb_t *got = cam_take(10);
    CHECK(got == NULL && give_count == 3 && receive_count == 3, "malformed cap failed"); return 1;
}
static int test_tick_wrap(void) {
    reset_case(); now_tick = UINT32_MAX - 2u; struct event e[] = {{&valid_fb, 5}}; set_events(e, 1);
    camera_fb_t *got = cam_take(10);
    CHECK(got == &valid_fb && receive_count == 1, "tick-wrap frame failed"); return 1;
}
static int test_zero_timeout(void) {
    reset_case(); struct event e[] = {{&valid_fb, 0}}; set_events(e, 1);
    CHECK(cam_take(0) == &valid_fb, "zero-timeout queued frame failed");
    reset_case(); CHECK(cam_take(0) == NULL && reset_count == 1 && receive_count == 2, "zero-timeout empty path failed"); return 1;
}
static int test_budget_exhausted(void) {
    reset_case(); struct event e[] = {{NULL, 10}, {NULL, 0}}; set_events(e, 2);
    CHECK(cam_take(10) == NULL && now_tick == 10 && receive_count == 2, "budget was reset or overrun"); return 1;
}
static int test_non_jpeg_metadata(void) {
    reset_case(); object.jpeg_mode = 0; valid_fb.len = 6; struct event e[] = {{&valid_fb, 0}}; set_events(e, 1);
    camera_fb_t *got = cam_take(1); CHECK(got == &valid_fb && got->len == 6, "non-JPEG metadata path failed"); return 1;
}
int main(void) {
    int ok = 1;
    ok &= test_valid(); ok &= test_empty_retry(); ok &= test_retry_success();
    ok &= test_malformed_then_valid(); ok &= test_malformed_cap(); ok &= test_tick_wrap();
    ok &= test_zero_timeout(); ok &= test_budget_exhausted(); ok &= test_non_jpeg_metadata();
    printf("%s\n", ok ? "9 cam_take cases passed" : "cam_take cases failed"); return ok ? 0 : 1;
}
'''

def main() -> int:
    import hashlib
    actual = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if actual != EXPECTED:
        raise SystemExit(f"cam_hal hash {actual} != {EXPECTED}; update is deliberate and manifest must be refreshed")
    src = SOURCE.read_text()
    start = src.index("camera_fb_t *cam_take(TickType_t timeout)")
    end = src.index("\nvoid cam_give(", start)
    function = src[start:end]
    with tempfile.TemporaryDirectory(prefix="camera-cam-take-") as td:
        td = pathlib.Path(td)
        cfile = td / "cam_take_harness.c"
        exe = td / "cam_take_harness"
        cfile.write_text(C_PREFIX + "\n" + function + "\n" + C_SUFFIX)
        cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", str(cfile), "-o", str(exe)]
        build = subprocess.run(cmd, text=True, capture_output=True)
        if build.returncode:
            print(build.stdout, end=""); print(build.stderr, end="")
            return build.returncode
        run = subprocess.run([str(exe)], text=True, capture_output=True)
        print(run.stdout, end=""); print(run.stderr, end="")
        result = {"source": SOURCE.relative_to(ROOT.parent.parent).as_posix(), "source_sha256": actual, "compile": build.returncode == 0, "run_exit": run.returncode, "cases": 9}
        (pathlib.Path(__file__).with_name("results.json")).write_text(json.dumps(result, indent=2) + "\n")
        return run.returncode

if __name__ == "__main__":
    raise SystemExit(main())
