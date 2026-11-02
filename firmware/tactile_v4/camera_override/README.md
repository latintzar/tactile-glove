# Camera driver override

This directory carries a narrow, hash-checked override for the pinned
`espressif/esp32-camera` 2.0.16 driver. The managed component under the IDF
build is left intact. `apply.cmake`, included after `project()`, verifies the
component source hashes, copies these reviewed sources into the build
configure directory, removes exactly the two matching managed translation
units from the camera target, and adds the generated copies.

The override has two behavioral changes. `cam_take()` uses one absolute
FreeRTOS tick budget across the initial queue receive, the single ESP32-S3
GDMA retry, and malformed-JPEG recovery. Corrupt frames with a null buffer or
fewer than two bytes are returned once and malformed recovery is capped at
three frames. `esp_camera_fb_get()` uses a 250 ms wait, while returned frame
metadata remains assigned by the public wrapper.

Pinned source hashes (from the managed 2.0.16 component):

- `driver/esp_camera.c`: `c39e6e65f7e68d13b481d2a86573ec049ef2b13004406336b874caadda3f7133`
- `driver/cam_hal.c`: `88a08e4a0b277172127840efe9ff736c8f1dcd51f3b31810ab32053297a7d902`

Reviewed source hashes:

- `driver/esp_camera.c`: `d8b3648076f5677ec69c2befbc7af34b31681a26df45838da47779f241dd69c2`
- `driver/cam_hal.c`: `3fc32b6c49ec15a0b9d9cd71ff1fce2e589f888cca2fddd4fb2b055554959836`

The host test extracts the actual reviewed `cam_take()` body at test time,
then compiles it with C11 AddressSanitizer and UndefinedBehaviorSanitizer
against queue/tick/DMA stubs. It covers valid frames, empty queue and GDMA
retry, malformed and capped recovery, tick wrap, zero timeout, exhausted
budget, and non-JPEG metadata preservation:

```text
python3 firmware/tactile_v4/camera_override/tests/test_cam_take.py
```

The test is a driver-control-flow test; it does not claim camera sensor,
GDMA hardware, image quality, or shutdown electrical validation.

Public redistribution adds an Apache 2.0 modification notice to `driver/cam_hal.c`; the current file SHA256 is `f81b24bee4eb3c1668a04bb90ae8b20c5d89396e3efede0fdc6a0280424ea700`. Its executable C body is unchanged from the reviewed hash above.

Public redistribution adds an Apache 2.0 modification notice to `driver/esp_camera.c`; the current file SHA256 is `e7a585a439eb142b9aaddf970d551506cfbb5890c1a19c074305b0ec577ee88a`. Its executable C body is unchanged from the reviewed hash above.
