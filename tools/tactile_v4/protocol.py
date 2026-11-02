"""Host decoder for the V4 TCP wire additions.

V4 keeps the V3 G3/COBS/CRC16 packet envelope (protocol version 2) and adds:
kind 6: anchored raw ISM330DHCX FIFO words plus source/rate/full-scale metadata;
kind 7: fixed-size V4 status counters and flags; kind 8: fixed-size NUL-terminated ASCII label;
kind 9: browser sensor/JPEG delivery counters, retained in recordings;
GV4J: length-delimited JPEG records with a first-DMA timestamp and a 512 KiB payload cap.

The firmware contract intentionally exposes FIFO words as raw seven-byte values.
This decoder preserves those bytes and applies ST's nominal sensitivity table.
Unit conversion does not establish calibration or continuity across FIFO gaps.
"""
from __future__ import annotations

import binascii
import struct
from dataclasses import dataclass
from typing import Any

HEADER = struct.Struct("<2sBBIQH")
CRC16 = struct.Struct("<H")
G3_MAGIC = b"G3"
G3_VERSION = 2
KIND_SCAN = 1
KIND_HEALTH = 2
KIND_SELECTED_RAW = 3
KIND_FEATURE = 4
KIND_IMU = 5
KIND_IMU_FIFO = 6
KIND_V4_STATUS = 7
KIND_LABEL = 8
KIND_BROWSER_STATUS = 9
SOURCE_CUFF = 0
SOURCE_HAND = 1
SOURCE_NAMES = {SOURCE_CUFF: "cuff", SOURCE_HAND: "dorsal-hand"}
JPEG_MAGIC = b"GV4J"
JPEG_HEADER_SIZE = 32
JPEG_TIMESTAMP_FIRST_DMA = 1
MAX_PACKET_ENCODED = 4096
MAX_JPEG_BYTES = 512 * 1024
FIFO_TAG_GYRO = 1
FIFO_TAG_ACCEL = 2
FIFO_TAG_TIMESTAMP = 4
FIFO_TAG_NAMES = {FIFO_TAG_GYRO: "gyro", FIFO_TAG_ACCEL: "accel", FIFO_TAG_TIMESTAMP: "timestamp"}
GYRO_FS_DPS = {0: 250, 1: 500, 2: 1000, 3: 2000}
# ST DS13012 Rev 7, table 3, page 10. A full-scale label divided by
# 32768 is NOT the gyro sensitivity (1000 dps uses 35 mdps/LSB).
ACCEL_G_PER_LSB = {2: 0.000061, 4: 0.000122, 8: 0.000244, 16: 0.000488}
GYRO_DPS_PER_LSB = {0: 0.00875, 1: 0.0175, 2: 0.035, 3: 0.07}


def crc16_ccitt(data: bytes) -> int:
    return binascii.crc_hqx(data, 0xFFFF)


def cobs_decode(encoded: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(encoded):
        code = encoded[i]
        if code == 0 or i + code > len(encoded):
            raise ValueError("cobs")
        i += 1
        end = min(i + code - 1, len(encoded))
        out.extend(encoded[i:end])
        i = end
        if code != 0xFF and i < len(encoded):
            out.append(0)
    return bytes(out)


def _signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def fifo_physical_axes(raw_axes: tuple[int, int, int], tag: int, *, accel_fs_g: int = 4,
                       gyro_fs_code: int = 2) -> tuple[float, float, float] | None:
    """Convert raw signed axes to nominal sensor units without calibration.

    The raw tuple and calibration status remain available to callers. This helper
    applies the manufacturer sensitivity for the declared full-scale setting.
    """
    if tag == FIFO_TAG_ACCEL:
        try:
            scale = ACCEL_G_PER_LSB[accel_fs_g]
        except KeyError as error:
            raise ValueError("accel_fs_g") from error
    elif tag == FIFO_TAG_GYRO:
        try:
            scale = GYRO_DPS_PER_LSB[gyro_fs_code]
        except KeyError as error:
            raise ValueError("gyro_fs_code") from error
    else:
        return None
    return tuple(value * scale for value in raw_axes)


def decode_fifo_word(raw_word: bytes, *, accel_fs_g: int = 4,
                     gyro_fs_code: int = 2) -> dict[str, Any]:
    """Decode one exact seven-byte FIFO word while retaining its raw bytes.

    The tag is the sensor tag field (the first byte shifted right by three).
    Timestamp records expose their raw 32-bit sensor ticks; their following two
    bytes stay in ``raw_word`` and are not interpreted. No sample interpolation
    or calibration is performed.
    """
    if len(raw_word) != 7:
        raise ValueError("fifo_word_length")
    raw = bytes(raw_word)
    tag = raw[0] >> 3
    result: dict[str, Any] = {
        "raw_word": raw,
        "tag": tag,
        "tag_name": FIFO_TAG_NAMES.get(tag, "unknown"),
        "raw_axes": None,
        "physical_axes": None,
        "timestamp_ticks": None,
        "calibrated": None,
    }
    if tag in (FIFO_TAG_GYRO, FIFO_TAG_ACCEL):
        raw_axes = struct.unpack_from("<hhh", raw, 1)
        result["raw_axes"] = raw_axes
        result["physical_axes"] = fifo_physical_axes(
            raw_axes, tag, accel_fs_g=accel_fs_g, gyro_fs_code=gyro_fs_code)
    elif tag == FIFO_TAG_TIMESTAMP:
        result["timestamp_ticks"] = struct.unpack_from("<I", raw, 1)[0]
    return result


def _base(raw: bytes) -> dict[str, Any]:
    magic, kind, version, seq, stamp, size = HEADER.unpack_from(raw)
    if magic != G3_MAGIC:
        raise ValueError("header")
    if version != G3_VERSION:
        raise ValueError(f"unsupported_version:{version}")
    if len(raw) != HEADER.size + size + CRC16.size:
        raise ValueError("length")
    expected = CRC16.unpack_from(raw, len(raw) - 2)[0]
    actual = crc16_ccitt(raw[:-2])
    if actual != expected:
        raise ValueError("crc16")
    return {"kind": kind, "protocol_version": version, "seq": seq, "t_us": stamp}


def decode_packet(encoded: bytes) -> dict[str, Any]:
    """Decode one COBS packet without its zero delimiter."""
    raw = cobs_decode(encoded)
    if len(raw) < HEADER.size + CRC16.size:
        raise ValueError("short")
    base = _base(raw)
    payload = raw[HEADER.size:-2]
    kind = base["kind"]
    if kind == KIND_IMU_FIFO:
        if len(payload) < 24:
            raise ValueError("imu_fifo_short")
        sensor_ticks, midpoint_us, uncertainty_us, flags, count, source_id = struct.unpack_from("<IQI HBB", payload)
        if count > 28 or len(payload) != 24 + 7 * count:
            raise ValueError("imu_fifo_length")
        odr_hz = struct.unpack_from("<H", payload, 20)[0]
        accel_fs_g = payload[22]
        gyro_fs_code = payload[23]
        if source_id > 1 or odr_hz == 0 or accel_fs_g not in ACCEL_G_PER_LSB or gyro_fs_code > 3:
            raise ValueError("imu_fifo_metadata")
        words = [bytes(payload[24 + 7 * i : 24 + 7 * (i + 1)]) for i in range(count)]
        return {
            **base,
            "sensor_ticks": sensor_ticks,
            "anchor_midpoint_us": midpoint_us,
            "anchor_uncertainty_us": uncertainty_us,
            "flags": flags,
            "count": count,
            "source_id": source_id,
            "source": SOURCE_NAMES[source_id],
            "odr_hz": odr_hz,
            "accel_fs_g": accel_fs_g,
            "gyro_fs_code": gyro_fs_code,
            "raw_words": words,
            "decoded_words": [decode_fifo_word(word, accel_fs_g=accel_fs_g,
                                                gyro_fs_code=gyro_fs_code)
                             for word in words],
            "calibrated": None,
            "calibration_status": "unavailable_until_assembly_calibration",
        }
    if kind == KIND_V4_STATUS:
        if len(payload) != 32:
            raise ValueError("status_length")
        (boot_id, returned_camera_frames, camera_drops, imu_overruns,
         odr_hz, capture_ring_drops, sd_drops, flags) = struct.unpack("<8I", payload)
        return {
            **base,
            "payload": payload,
            "boot_id": boot_id,
            "returned_camera_frames": returned_camera_frames,
            "camera_drops": camera_drops,
            "imu_overruns": imu_overruns,
            "odr_hz": odr_hz,
            "capture_ring_drops": capture_ring_drops,
            "sd_drops": sd_drops,
            "flags": flags,
            "sd_mounted": bool(flags & 1),
            "camera_stopped": bool(flags & 2),
            "cuff_imu_stale": bool(flags & 4),
            "hand_imu_stale": bool(flags & 8),
            "control_i2c_failure": bool(flags & 16),
        }
    if kind == KIND_BROWSER_STATUS:
        if len(payload) != 8:
            raise ValueError("browser_status_length")
        sensor_drops, jpeg_drops = struct.unpack("<II", payload)
        return {**base, "payload": payload, "browser_sensor_drops": sensor_drops,
                "browser_jpeg_drops": jpeg_drops}
    if kind == KIND_LABEL:
        if len(payload) != 13:
            raise ValueError("label_length")
        nul = payload.find(b"\x00")
        if nul < 0 or any(payload[nul:]):
            raise ValueError("label_termination")
        label_bytes = payload[:nul]
        if any(byte < 0x20 or byte > 0x7E for byte in label_bytes):
            raise ValueError("label_ascii")
        return {**base, "payload": payload, "label": label_bytes.decode("ascii")}
    if kind == KIND_SCAN:
        if len(payload) != 94:
            raise ValueError("scan_size")
        index, flags, dynamic_hz, pressure_hz, imu_lo = struct.unpack_from("<IHHHH", payload)
        imu_hi = struct.unpack_from("<H", payload, 12)[0]
        values = struct.unpack_from("<40H", payload, 14)
        pressure = [_signed16(x) for x in values[:20]]
        dynamic = [_signed16(x) for x in values[20:]]
        return {**base, "index": index, "flags": flags, "dynamic_hz": dynamic_hz,
                "pressure_hz": pressure_hz, "imu_timestamp": imu_lo | imu_hi << 16,
                "pressure_raw": pressure, "dynamic_raw": dynamic}
    if kind == KIND_HEALTH:
        return {**base, "payload": payload}
    if kind == KIND_SELECTED_RAW:
        return {**base, "payload": payload}
    if kind == KIND_FEATURE:
        return {**base, "payload": payload}
    if kind == KIND_IMU:
        return {**base, "payload": payload}
    return {**base, "payload": payload}


def map_sensor_tick(anchor: dict[str, Any], sensor_ticks: int) -> tuple[int, int] | None:
    """Map one 32-bit sensor tick to host microseconds and uncertainty.

    The firmware contract defines 40 kHz sensor ticks (25 us). Signed modular
    subtraction handles one wrap; values older than half the tick range are
    rejected rather than assigned a fabricated timestamp.
    """
    if not 0 <= sensor_ticks <= 0xFFFFFFFF:
        raise ValueError("sensor_ticks")
    anchor_tick = anchor["sensor_ticks"]
    delta = (sensor_ticks - anchor_tick) & 0xFFFFFFFF
    if delta >= 0x80000000:
        delta -= 0x100000000
    stamp = anchor["anchor_midpoint_us"] + delta * 25
    if stamp < 0:
        return None
    return stamp, anchor["anchor_uncertainty_us"]


@dataclass
class PacketStreamDecoder:
    """Fragment/coalesce-safe G3 stream decoder with accepted-frame gap counts."""
    buffer: bytearray
    last_seq: int | None = None
    sequence_gaps: int = 0
    rejected_frames: int = 0
    max_frame_bytes: int = MAX_PACKET_ENCODED
    _discard_until_delimiter: bool = False

    def __init__(self, max_frame_bytes: int = MAX_PACKET_ENCODED) -> None:
        if max_frame_bytes < HEADER.size + CRC16.size:
            raise ValueError("max_frame_bytes")
        self.buffer = bytearray()
        self.last_seq = None
        self.sequence_gaps = 0
        self.rejected_frames = 0
        self.max_frame_bytes = max_frame_bytes
        self._discard_until_delimiter = False

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        for byte in data:
            if byte:
                if self._discard_until_delimiter:
                    continue
                if len(self.buffer) >= self.max_frame_bytes:
                    self.buffer.clear()
                    self._discard_until_delimiter = True
                    self.rejected_frames += 1
                    continue
                self.buffer.append(byte)
                continue
            if self._discard_until_delimiter:
                self._discard_until_delimiter = False
                continue
            if not self.buffer:
                continue
            encoded = bytes(self.buffer)
            self.buffer.clear()
            try:
                frame = decode_packet(encoded)
            except ValueError:
                self.rejected_frames += 1
                continue
            if self.last_seq is not None:
                delta = (frame["seq"] - self.last_seq) & 0xFFFFFFFF
                if delta > 1:
                    self.sequence_gaps += delta - 1
            self.last_seq = frame["seq"]
            frames.append(frame)
        return frames


@dataclass
class JpegStreamDecoder:
    """Fragment/coalesce-safe GV4J TCP record decoder."""
    buffer: bytearray
    last_seq: int | None = None
    sequence_gaps: int = 0
    rejected_records: int = 0

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.last_seq = None
        self.sequence_gaps = 0
        self.rejected_records = 0

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        self.buffer.extend(data)
        records: list[dict[str, Any]] = []
        while True:
            if len(self.buffer) < JPEG_HEADER_SIZE:
                break
            if self.buffer[:4] != JPEG_MAGIC:
                del self.buffer[0]
                self.rejected_records += 1
                continue
            header = bytes(self.buffer[:JPEG_HEADER_SIZE])
            seq, stamp, size, data_crc, width, height, origin, header_crc = struct.unpack_from("<IQIIHHHH", header, 4)
            if origin != JPEG_TIMESTAMP_FIRST_DMA or crc16_ccitt(header[:30]) != header_crc:
                del self.buffer[:4]
                self.rejected_records += 1
                continue
            if size > MAX_JPEG_BYTES:
                del self.buffer[:4]
                self.rejected_records += 1
                continue
            total = JPEG_HEADER_SIZE + size
            if len(self.buffer) < total:
                break
            jpeg = bytes(self.buffer[JPEG_HEADER_SIZE:total])
            del self.buffer[:total]
            if (binascii.crc32(jpeg) & 0xFFFFFFFF) != data_crc:
                self.rejected_records += 1
                continue
            if self.last_seq is not None:
                delta = (seq - self.last_seq) & 0xFFFFFFFF
                if delta > 1:
                    self.sequence_gaps += delta - 1
            self.last_seq = seq
            records.append({"seq": seq, "stamp_us": stamp, "jpeg": jpeg, "jpeg_bytes": size,
                            "width": width, "height": height, "timestamp_origin": "first_dma"})
        return records
