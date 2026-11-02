#!/usr/bin/env python3
"""Copy the reviewed camera driver override after checking pinned inputs."""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path

FILES = ("esp_camera.c", "cam_hal.c")
PINNED = {
    "esp_camera.c": "c39e6e65f7e68d13b481d2a86573ec049ef2b13004406336b874caadda3f7133",
    "cam_hal.c": "88a08e4a0b277172127840efe9ff736c8f1dcd51f3b31810ab32053297a7d902",
}
OVERRIDE = {
    "esp_camera.c": "e7a585a439eb142b9aaddf970d551506cfbb5890c1a19c074305b0ec577ee88a",
    "cam_hal.c": "f81b24bee4eb3c1668a04bb90ae8b20c5d89396e3efede0fdc6a0280424ea700",
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def check(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise SystemExit(f"camera override: missing {label}: {path}")
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(f"camera override: {label} hash {actual} != expected {expected}")
    return actual

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--override-root", type=Path, default=Path(__file__).resolve().parent / "driver")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    pinned = {name: check(args.source_root / name, expected, f"pinned {name}") for name, expected in PINNED.items()}
    overrides = {name: check(args.override_root / name, expected, f"reviewed {name}") for name, expected in OVERRIDE.items()}
    # This is a tool-owned configure directory. Reconfigure is idempotent, but
    # a foreign file in the directory is rejected rather than overwritten.
    allowed = set(FILES) | {"manifest.json"}
    if args.output.exists():
        unexpected = {entry.name for entry in args.output.iterdir()} - allowed
        if unexpected:
            names = ", ".join(sorted(unexpected))
            raise SystemExit(f"camera override: foreign output files: {names}")
    args.output.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copyfile(args.override_root / name, args.output / name)
        if sha256(args.output / name) != overrides[name]:
            raise SystemExit(f"camera override: copied {name} changed during configure")
    manifest = {
        "schema": 1,
        "pinned_component": "espressif/esp32-camera 2.0.16",
        "pinned_sources": pinned,
        "reviewed_sources": overrides,
        "generated_sources": {name: sha256(args.output / name) for name in FILES},
        "changes": [
            "cam_take uses one absolute TickType_t budget for queue receive, one ESP32-S3 GDMA retry, and malformed-JPEG recovery; malformed frames are returned once and capped at three",
            "esp_camera_fb_get uses a 250 ms public wait",
        ],
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
