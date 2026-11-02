"""Independent decoding of the actual native acquisition core fed the SPICE trace."""
import csv
import math
import struct
from pathlib import Path
from tools.tactile_v4.protocol import PacketStreamDecoder, KIND_SCAN, KIND_FEATURE


def test_actual_core_piezo_waveform_and_feature_values():
    root = Path(__file__).resolve().parents[2]
    csv_path = root / "hardware/glove-v3/verification/signal-chain/piezo-to-firmware.csv"
    with csv_path.open() as handle:
        expected = [int(row["dynamic_code"]) for row in csv.DictReader(handle)]
    wire = (root / "firmware/tactile_v4/artifacts/native-actual-core.bin.piezo").read_bytes()
    decoder = PacketStreamDecoder()
    frames = []
    for start in range(0, len(wire), 17):
        frames += decoder.feed(wire[start:start + 17])
    scans = [frame for frame in frames if frame["kind"] == KIND_SCAN]
    features = [frame for frame in frames if frame["kind"] == KIND_FEATURE]
    assert len(scans) == len(expected) == 520
    assert len(features) == 6
    assert [frame["dynamic_raw"][0] for frame in scans] == expected
    assert [frame["t_us"] for frame in scans] == [i * 250 for i in range(520)]
    assert all(frame["dynamic_raw"][1:] == [0] * 19 for frame in scans)
    assert all(frame["pressure_raw"] == [0] * 20 for frame in scans)
    assert all(frame["flags"] == 4 for frame in scans)  # Physical mux timing remains unverified.
    for window, frame in enumerate(features):
        payload = frame["payload"]
        first, flags, count = struct.unpack_from("<IHH", payload)
        values = expected[window * 80:(window + 1) * 80]
        assert (first, flags, count) == (window * 80, 4, 80)
        assert frame["t_us"] == window * 80 * 250
        assert struct.unpack_from("<20h", payload, 8) == (0,) * 20
        assert struct.unpack_from("<H", payload, 48)[0] == math.isqrt(sum(x * x for x in values) // 80)
        assert struct.unpack_from("<H", payload, 88)[0] == max(abs(x) for x in values)
    assert decoder.rejected_frames == 0 and decoder.sequence_gaps == 0
