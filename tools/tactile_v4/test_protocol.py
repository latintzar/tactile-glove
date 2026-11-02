import binascii
import struct
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import protocol


def cobs_encode(raw):
    out=bytearray([0]); code=1; code_at=0
    for b in raw:
        if b == 0:
            out[code_at]=code; code_at=len(out); out.append(0); code=1
        else:
            out.append(b); code += 1
            if code == 0xFF:
                out[code_at]=code; code_at=len(out); out.append(0); code=1
    out[code_at]=code; out.append(0); return bytes(out)


def packet(kind, seq, stamp, payload):
    head=struct.pack('<2sBBIQH',b'G3',kind,2,seq,stamp,len(payload)); body=head+payload
    return cobs_encode(body+struct.pack('<H',protocol.crc16_ccitt(body)))


def imu_packet(seq=0, ticks=0xFFFFFFFE):
    words=bytes(range(7))+bytes(range(7,14))
    payload=struct.pack('<IQIHBB',ticks,9_000_000,40,3,2,0)+struct.pack('<HBB',833,4,2)+words
    return packet(6,seq,9_000_000,payload)


def jpeg(seq,stamp,data=b'\xff\xd8fake\xff\xd9'):
    head=bytearray(32); head[:4]=b'GV4J'; struct.pack_into('<IQIIHHH',head,4,seq,stamp,len(data),binascii.crc32(data)&0xffffffff,640,480,1); struct.pack_into('<H',head,30,protocol.crc16_ccitt(head[:30])); return bytes(head)+data


def status_payload(boot=0xA4715A4E, frames=17, camera_drops=18, imu_overruns=19,
                  odr=833, capture_drops=20, sd_drops=21, flags=0x1D):
    return struct.pack('<8I', boot, frames, camera_drops, imu_overruns, odr,
                       capture_drops, sd_drops, flags)


def test_imu_anchor_preserves_raw_and_does_not_invent_calibration():
    frame=protocol.decode_packet(imu_packet()[:-1])
    assert frame['sensor_ticks']==0xFFFFFFFE and frame['raw_words'][0]==bytes(range(7))
    assert (frame['source_id'],frame['odr_hz'],frame['accel_fs_g'],frame['gyro_fs_code'])==(0,833,4,2)
    assert frame['calibrated'] is None
    assert protocol.map_sensor_tick(frame,1)==(9_000_000+3*25,40)


def test_packet_fragmentation_coalescing_and_wrap_gap():
    stream=protocol.PacketStreamDecoder(); data=packet(7,0xFFFFFFFF,1,status_payload())+packet(7,1,2,status_payload())+packet(7,4,3,status_payload())
    got=[]
    for i in range(0,len(data),3): got += stream.feed(data[i:i+3])
    assert [x['seq'] for x in got]==[0xFFFFFFFF,1,4] and stream.sequence_gaps==3


def test_bad_crc_is_rejected_and_next_frame_recovers():
    bad=bytearray(packet(7,1,1,status_payload())); bad[-3]^=1
    stream=protocol.PacketStreamDecoder(); assert stream.feed(bytes(bad)+packet(7,2,2,status_payload()))[-1]['seq']==2; assert stream.rejected_frames==1


def test_imu_malformed_count_is_rejected():
    payload=struct.pack('<IQIHBB',1,2,3,0,29,0)+struct.pack('<HBB',833,4,2)+b'x'*203
    try: protocol.decode_packet(packet(6,1,2,payload)[:-1])
    except ValueError as e: assert str(e)=='imu_fifo_length'
    else: assert False


def test_fifo_tag_records_keep_raw_and_apply_nominal_physical_scale():
    gyro = bytes([protocol.FIFO_TAG_GYRO << 3]) + struct.pack('<hhh', -32768, 0, 32767)
    accel = bytes([protocol.FIFO_TAG_ACCEL << 3]) + struct.pack('<hhh', -16384, 0, 16384)
    timestamp = bytes([protocol.FIFO_TAG_TIMESTAMP << 3]) + struct.pack('<I', 0x12345678) + b'\xaa\xbb'
    g = protocol.decode_fifo_word(gyro)
    a = protocol.decode_fifo_word(accel)
    t = protocol.decode_fifo_word(timestamp)
    assert g['raw_word'] == gyro and g['tag_name'] == 'gyro' and g['raw_axes'] == (-32768,0,32767)
    assert g['physical_axes'] == pytest.approx((-1146.88, 0.0, 1146.845))
    assert a['tag_name'] == 'accel' and a['physical_axes'] == pytest.approx((-1.998848, 0.0, 1.998848))
    assert t['tag_name'] == 'timestamp' and t['timestamp_ticks'] == 0x12345678
    assert t['physical_axes'] is None and t['raw_word'] == timestamp and t['calibrated'] is None


def test_packet_stream_bounds_zero_free_noise_and_recovers():
    stream = protocol.PacketStreamDecoder(max_frame_bytes=64)
    valid = packet(7, 20, 21, status_payload())
    got = stream.feed(b'A' * 65 + b'\x00' + valid)
    assert [frame['seq'] for frame in got] == [20]
    assert stream.rejected_frames == 1 and len(stream.buffer) == 0


def test_jpeg_fragmented_and_timestamp_wrap_gap():
    rec=protocol.JpegStreamDecoder(); data=jpeg(0xFFFFFFFF,100)+jpeg(1,125)+jpeg(4,150); got=[]
    for i in range(0,len(data),5): got += rec.feed(data[i:i+5])
    assert [x['seq'] for x in got]==[0xFFFFFFFF,1,4] and rec.sequence_gaps==3
    assert got[1]['stamp_us']==125 and got[1]['timestamp_origin']=='first_dma'


def test_jpeg_bad_crc_and_truncated_wait():
    data=bytearray(jpeg(2,200)); data[-1]^=1; rec=protocol.JpegStreamDecoder(); assert rec.feed(bytes(data[:10]))==[]; assert rec.feed(bytes(data[10:]))==[]; assert rec.rejected_records==1


def test_jpeg_oversize_header_rejects_and_recovers():
    head=bytearray(32); head[:4]=b'GV4J'
    struct.pack_into('<IQIIHHH', head, 4, 3, 300, protocol.MAX_JPEG_BYTES + 1, 0, 640, 480, 1)
    struct.pack_into('<H', head, 30, protocol.crc16_ccitt(head[:30]))
    rec=protocol.JpegStreamDecoder()
    got=rec.feed(bytes(head) + jpeg(4,325))
    assert [record['seq'] for record in got] == [4]
    assert rec.rejected_records >= 1


def test_status_payload_fields_and_bad_version_are_explicit():
    payload = status_payload()
    frame=protocol.decode_packet(packet(7,8,9,payload)[:-1])
    assert frame["payload"]==payload
    assert (frame["boot_id"], frame["returned_camera_frames"], frame["camera_drops"],
            frame["imu_overruns"], frame["odr_hz"], frame["capture_ring_drops"],
            frame["sd_drops"], frame["flags"]) == (0xA4715A4E,17,18,19,833,20,21,0x1D)
    assert all(frame[name] for name in ("sd_mounted", "cuff_imu_stale", "hand_imu_stale",
                                        "control_i2c_failure"))
    assert frame["camera_stopped"] is False
    for malformed in (b"", b"x"*31, b"x"*33):
        try: protocol.decode_packet(packet(7,8,9,malformed)[:-1])
        except ValueError as e: assert str(e)=="status_length"
        else: assert False
    bad=bytearray(packet(7,9,10,status_payload())[:-1])
    raw=bytearray(protocol.cobs_decode(bytes(bad))); raw[3]=1
    bad_version=cobs_encode(bytes(raw))[:-1]
    try: protocol.decode_packet(bad_version)
    except ValueError as e: assert str(e)=="unsupported_version:1"
    else: assert False


def test_label_kind_requires_thirteen_byte_nul_terminated_ascii_payload():
    frame = protocol.decode_packet(packet(protocol.KIND_LABEL, 11, 12, b"HAND IMU 001\x00")[:-1])
    assert frame["label"] == "HAND IMU 001"
    assert frame["payload"] == b"HAND IMU 001\x00"
    for malformed in (b"ABCDEFGHIJKLM", b"ABC\x00DEF\x00\x00\x00\x00\x00\x00", b"ABC\xff" + b"\x00" * 9):
        try:
            protocol.decode_packet(packet(protocol.KIND_LABEL, 12, 13, malformed)[:-1])
        except ValueError as error:
            assert str(error) in {"label_termination", "label_ascii"}
        else:
            assert False


def test_timestamp_rejects_ambiguous_old_sample():
    anchor={"sensor_ticks":100,"anchor_midpoint_us":1000,"anchor_uncertainty_us":25}
    assert protocol.map_sensor_tick(anchor,99)==(975,25)
    assert protocol.map_sensor_tick(anchor,0x80000064) is None


def test_jpeg_header_crc_is_rejected_and_valid_record_follows():
    bad=bytearray(jpeg(3,300)); bad[28]^=1
    rec=protocol.JpegStreamDecoder()
    assert rec.feed(bytes(bad)+jpeg(4,325))[-1]["seq"]==4
    assert rec.rejected_records>=1


def test_truncated_cobs_code_is_rejected():
    try: protocol.decode_packet(b"\x02")
    except ValueError as e: assert str(e)=="cobs"
    else: assert False


def test_native_core_sample_decodes_actual_firmware_bytes():
    import pytest
    fixture=Path(__file__).parents[2]/"hardware/glove-v4/verification/native/actual-core-sample.bin"
    if not fixture.exists(): pytest.skip("native fixture not installed")
    stream=protocol.PacketStreamDecoder(); got=stream.feed(fixture.read_bytes())
    assert [x["seq"] for x in got]==[0,1,3999]
    assert [x["t_us"] for x in got]==[0,250,999750]
    assert got[0]["kind"]==protocol.KIND_SCAN and len(got[0]["dynamic_raw"])==20
    assert got[0]["dynamic_raw"][0]==-60 and got[0]["dynamic_raw"][19]==73
    assert stream.rejected_frames==0 and stream.sequence_gaps==3997


def test_imu_metadata_enum_is_validated():
    payload=bytearray(struct.pack('<IQIHBB',1,2,3,0,0,0)+struct.pack('<HBB',833,4,2))
    payload[19]=2
    try: protocol.decode_packet(packet(6,1,2,bytes(payload))[:-1])
    except ValueError as e: assert str(e)=="imu_fifo_metadata"
    else: assert False


def test_native_imu_status_fixture_decodes_both_sources_and_raw_words():
    fixture=Path(__file__).parents[2]/"hardware/glove-v4/verification/native/actual-core.bin.imu-status"
    data=fixture.read_bytes()
    stream=protocol.PacketStreamDecoder(); got=[]
    for i in range(0,len(data),7): got += stream.feed(data[i:i+7])
    assert [x["kind"] for x in got]==[protocol.KIND_IMU_FIFO,protocol.KIND_IMU_FIFO,protocol.KIND_V4_STATUS]
    assert [x["source_id"] for x in got[:2]]==[0,1]
    assert [x["source"] for x in got[:2]]==["cuff", "dorsal-hand"]
    assert all((x["odr_hz"],x["accel_fs_g"],x["gyro_fs_code"])==(833,4,2) for x in got[:2])
    assert all(x["flags"]==4 and x["count"]==2 for x in got[:2])
    assert got[0]["raw_words"]==[bytes.fromhex("20100000000000"),bytes(7)]
    assert got[1]["raw_words"]==[bytes.fromhex("20100000000000"),bytes(7)]
    assert protocol.map_sensor_tick(got[0],got[0]["sensor_ticks"])==(1_000_000,125)
    assert got[2]["payload"]==bytes.fromhex("4e5a71a400000000000000000000000041030000000000000000000001000000")
    assert (got[2]["boot_id"], got[2]["returned_camera_frames"], got[2]["odr_hz"],
            got[2]["flags"]) == (0xA4715A4E, 0, 833, 1)
    assert got[2]["sd_mounted"] is True and got[2]["camera_stopped"] is False
    assert stream.rejected_frames==0 and stream.sequence_gaps==0


def test_native_label_fixture_decodes_nul_padded_ascii():
    fixture=Path(__file__).parents[2]/"hardware/glove-v4/verification/native/actual-core.bin.label"
    if not fixture.exists():
        import pytest; pytest.skip("native label fixture not installed")
    stream=protocol.PacketStreamDecoder(); got=stream.feed(fixture.read_bytes())
    assert len(got)==1 and got[0]["kind"]==protocol.KIND_LABEL
    assert got[0]["seq"]==9003 and got[0]["t_us"]==1_000_001
    assert got[0]["label"]=="TEST/1"
    assert got[0]["payload"]==b"TEST/1"+b"\x00"*7
    assert stream.rejected_frames==0


def test_native_jpeg_fixture_decodes_first_dma_timestamp_and_crc():
    fixture=Path(__file__).parents[2]/"hardware/glove-v4/verification/native/actual-core.bin.jpeg"
    data=fixture.read_bytes(); stream=protocol.JpegStreamDecoder(); got=[]
    for i in range(0,len(data),4): got += stream.feed(data[i:i+4])
    assert len(got)==1 and got[0]["seq"]==7
    assert got[0]["stamp_us"]==0x1_0000_0001 and got[0]["timestamp_origin"]=="first_dma"
    assert (got[0]["width"],got[0]["height"],got[0]["jpeg"])==(640,480,b"\xff\xd8\x01\x02\xff\xd9")
    assert stream.rejected_records==0


def test_native_http_loss_status_fixture():
    fixture=Path(__file__).parents[2]/"firmware/tactile_v4/artifacts/native-actual-core.bin.browser-status"
    stream=protocol.PacketStreamDecoder(); frames=stream.feed(fixture.read_bytes())
    assert len(frames)==1 and frames[0]["kind"]==protocol.KIND_BROWSER_STATUS
    assert frames[0]["browser_sensor_drops"]==7
    assert frames[0]["browser_jpeg_drops"]==1
    assert stream.rejected_frames==0


def test_browser_status_requires_exact_eight_bytes():
    import pytest
    for length in (0,7,9,32):
        with pytest.raises(ValueError,match="browser_status_length"):
            protocol.decode_packet(packet(9,0,0,bytes(length))[:-1])


def test_actual_pipeline_keeps_features_while_raw_is_selected():
    fixture=Path(__file__).parents[2]/"firmware/tactile_v4/artifacts/native-actual-core.bin.dual-mode"
    stream=protocol.PacketStreamDecoder(); frames=stream.feed(fixture.read_bytes())
    assert len(frames)==151 and stream.rejected_frames==stream.sequence_gaps==0
    features=[f for f in frames if f["kind"]==protocol.KIND_FEATURE]
    selected=[f for f in frames if f["kind"]==protocol.KIND_SELECTED_RAW]
    assert len(features)==51 and len(selected)==100
    assert all(struct.unpack_from("<H",f["payload"],4)[0]==20 for f in selected)
    assert [f["t_us"] for f in features]==list(range(0,1_020_000,20_000))
    assert [f["t_us"] for f in selected]==list(range(0,1_000_000,10_000))


@pytest.mark.parametrize('tag,accel_range,gyro_code,expected', [
    (1,4,0,8.75), (1,4,1,17.5), (1,4,2,35.0), (1,4,3,70.0),
    (2,2,2,0.061), (2,4,2,0.122), (2,8,2,0.244), (2,16,2,0.488),
])
def test_manufacturer_sensitivity_vectors(tag,accel_range,gyro_code,expected):
    # Independent conversion vectors from DS13012 Rev 7 table 3, page 10.
    # 1000 raw counts at ±1000 dps is 35 dps, not 30.5176 dps.
    word=bytes([tag<<3])+struct.pack('<hhh',1000,0,-1000)
    decoded=protocol.decode_fifo_word(word,accel_fs_g=accel_range,gyro_fs_code=gyro_code)
    assert decoded['physical_axes']==pytest.approx((expected,0,-expected))
    assert decoded['raw_word']==word and decoded['calibrated'] is None


def test_imu_unknown_accelerometer_range_is_rejected():
    payload=struct.pack('<IQIHBB',1,2,3,0,0,0)+struct.pack('<HBB',833,3,2)
    with pytest.raises(ValueError,match='imu_fifo_metadata'):
        protocol.decode_packet(packet(6,1,2,payload)[:-1])
