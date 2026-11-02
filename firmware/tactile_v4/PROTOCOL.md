# V4 wire additions

All G3 packets retain the V3 version2 envelope:COBS with zero delimiter;decoded header `<2sBBIQH>` = `G3`,kind,version2,sequence32,timestamp64microseconds,payload length16;payload;CRC16-CCITT(initial0xFFFF) over header+payload. All integers below are little-endian. Existing kinds1–4 and42-byte health configuration remain unchanged. USB/Wi-Fi/SD share sequence space;BLE and the browser each have separate sequence spaces because they intentionally exclude full4kHz scans.

## Kind6:dual IMU FIFO

| Offset | Field |
|---:|---|
|0|Current sensor timestamp ticks,u32 |
|4|MCU midpoint of timestamp I2C transaction,u64µs |
|12|Anchor uncertainty,u32µs |
|16|Flags,u16:bit0overrun,bit1awaiting new timestamp,bit2raw factory axes/scale |
|18|Record count,u8,0…28 |
|19|Source,u8:0=cuff0x6A,1=hand0x6B |
|20|ODR,u16,833Hz |
|22|Accelerometer full scale,u8,4g |
|23|Gyroscope scale enum,u8,2=1000dps;0/1/2/3 map250/500/1000/2000dps |
|24|Count×7 exact tagged FIFO bytes |

The packet timestamp equals the anchor MCU midpoint. A zero-count packet can report overrun recovery. Tag4 contains sensor timestamp;the host retains raw tag-counter semantics and distinct sensor clocks. IMU FIFO read time is not a sample time.

## Kind7:status

32-byte payload,u32fields at offsets0boot ID,4returned camera frames,8camera/allocation/network drops,12IMU overruns,16ODR833,20capture-ring drops,24SD drops,28flags. Flags:bit0SD mounted,bit1camera stopped,bit2cuff IMU stale,bit3hand IMU stale,bit4control-I2C failure observed. Camera drop counts include intentional10fps pacing skips and unsuccessful network queue delivery even when SD retained that frame. Driver-internal skipped frames are not fully observable through this count.

## Kind8:label

Exactly13bytes:NUL-terminated uppercase ASCII label(max12characters),zero padding. Empty label is the initial state. Accepted characters:A–Z,0–9,space,hyphen,slash. The current boot/session label emits immediately on change and once per second,including while tactile capture is paused.

## JPEG TCP7001 and `.gv4j`

32-byte header followed by exactly the declared JPEG length:

| Offset | Field |
|---:|---|
|0|`GV4J` |
|4|Frame sequence,u32 |
|8|First-DMA ESP timer timestamp,u64µs |
|16|JPEG bytes,u32 |
|20|JPEG CRC32(IEEE),u32 |
|24,26|Width,height,u16 each |
|28|Flags,u16;bit0=first-DMA timestamp |
|30|CRC16-CCITT over first30header bytes |

JPEG allocation is bounded to512KiB per frame. Sequence gaps and counters expose transport/storage loss. Header CRC protects framing;JPEG CRC protects payload. First-DMA time carries an unknown exposure offset until sensor timing is measured.

## HTTP browser stream

`GET /` serves the embedded gzip viewer. `GET /ws` upgrades one browser session. Each binary WebSocket message contains one complete record:

- Prefix byte0: one complete G3 COBS packet, including its zero delimiter. Kinds2/3/4/6/7/8/9 are eligible; full scan kind1 is excluded. The browser G3 sequence advances on each eligible enqueue attempt, so queue loss is visible as a gap. Sequences remain monotonic across reconnects during the boot.
- Prefix byte1: one complete32-byte GV4J header followed by the declared JPEG bytes. The original camera sequence/timestamp/CRC are preserved. A latest-frame reference replaces stale preview frames while SD/TCP retain independent queues.

Commands are complete unfragmented text frames, maximum31bytes: `FEATURES`, `RAW 0` through `RAW 39`, or `LABEL TEXT`. Invalid/overflowed commands close that browser session; state changes take effect through the existing shared command queue. Feature packets continue during RAW mode on USB/TCP/SD/browser. BLE transmits features in FEATURES mode or selected waveform in RAW mode, plus health/status/labels.

The server has a64-packet PSRAM browser queue and an independent sequence counter. Each WS frame has a200ms total socket-send deadline. A slow/closed viewer cannot retain a camera-driver buffer or consume SD/TCP queues. The access boundary is the per-device WPA2 network key; browser Origin must match the cuff Host. Native clients may omit Origin. IDF5.4 calls the route handler after sending the upgrade; rejected sessions are therefore immediately closed rather than receiving another HTTP response.

## Kind9:browser delivery status

Exactly8bytes:LEu32 at0 counts browser sensor-packet drops;LEu32 at4 counts browser JPEG preview drops. Counters accumulate during the current boot and wrap modulo2^32. Sensor drops include browser queue overflow, failed socket delivery and queued packets discarded on disconnect. JPEG drops include replacing a latest frame before it is claimed for transmission, failed transmission, and an unclaimed latest frame discarded on disconnect. An in-flight JPEG keeps its reference and is counted once if its send fails. Upstream camera sequence gaps remain a separate metric.

This payload emits once per second on USB/TCP/SD/browser, so a recording retains browser delivery history. BLE keeps its existing smaller status set. Kind7 remains32bytes with its existing semantics.
