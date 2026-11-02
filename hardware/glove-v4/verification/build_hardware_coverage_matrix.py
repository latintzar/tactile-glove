#!/usr/bin/env python3
"""Build the V4 hardware evidence coverage matrix.

This is an inventory and provenance report, not a claim that every component
has been physically simulated.  Each manifest row is assigned exactly once to
its subsystem block, and each block records the strongest evidence currently
available plus the physical qualification that remains open.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VERIFY = ROOT / "hardware/glove-v4/verification"
MANIFEST = ROOT / "hardware/glove-v4/electrical/components.json"
JSON_OUT = VERIFY / "hardware-coverage-matrix.json"
MD_OUT = VERIFY / "hardware-coverage-matrix.md"


EVIDENCE = {
    "tactile": [
        "hardware/glove-v4/verification/analog-coverage-2026-10-23.json",
        "hardware/glove-v4/verification/differential-adc/results.json",
        "hardware/glove-v4/verification/coupled-analog/results.json",
        "hardware/glove-v4/verification/coupled-analog/diagnostics/conditioning/results.json",
        "firmware/tactile_v4/artifacts/verification-summary.json",
        "hardware/glove-v4/verification/shutdown/README.md",
        "hardware/glove-v3/verification/signal-chain/results.json",
        "hardware/glove-v3/verification/mux-adc/results.json",
        "hardware/glove-v3/verification/power-simulation.md",
        "hardware/glove-v3/simulation/power_validation/rerun-results.json",
        "hardware/glove-v3/verification/firmware-simulation.md",
        "hardware/glove-v3/verification/signal-chain/piezo-to-firmware.json",
    ],
    "power": [
        "hardware/glove-v4/power/power-check-results.json",
        "hardware/glove-v4/power/simulation/buck-results.json",
        "hardware/glove-v4/power/simulation/latest-runs.json",
        "hardware/glove-v4/verification/energy-budget.json",
        "hardware/glove-v4/power/simulation/finite-path-followup.json",
        "hardware/glove-v4/power/finite-path-backend-diagnostics/results.json",
        "hardware/glove-v4/verification/thermal-screen/results.json",
        "hardware/glove-v4/verification/thermal-screen/readout-proposal/results.json",
        "hardware/glove-v4/verification/thermal-screen/readout-proposal/buffer-results.json",
        "hardware/glove-v4/verification/thermal-screen/readout-proposal/firmware/results.json",
    ],
    "camera": [
        "hardware/glove-v4/interfaces/camera-interface-checks.json",
        "hardware/glove-v4/interfaces/camera-interface.json",
        "hardware/glove-v4/verification/browser-wire-fixture.json",
    ],
    "imu": [
        "hardware/glove-v4/interfaces/imu-interface-checks.json",
        "hardware/glove-v4/interfaces/imu-interface.json",
        "hardware/glove-v4/verification/native/actual-core.bin.imu-status",
        "hardware/glove-v4/verification/v4-host-decoder.md",
    ],
    "sd": [
        "hardware/glove-v4/interfaces/sd-interface.json",
        "hardware/glove-v4/interfaces/sd-source-evidence.json",
    ],
}


BLOCKS = {
    "tactile": {
        "coverage_classes": [
            "static_check",
            "simulation_model_proxy",
            "host_firmware_fixture",
            "physical_pending",
        ],
        "status": "model_proxy_and_host_fixture; physical qualification pending",
        "boundary": (
            "Inherited V3 signal-chain and mux decks cover the reviewed topology "
            "and proxy loading. V4 differential ADC settling has five completed native cases. V4 rail coupling and physical sensor/cable behavior "
            "remain open."
        ),
    },
    "power": {
        "coverage_classes": ["static_check", "simulation_model_proxy", "physical_pending"],
        "status": "static_and_partial_native_run; finite-impedance and physical qualification pending",
        "boundary": (
            "Power arithmetic and selected buck execution are evidenced. The "
            "finite-impedance rail qualification and thermal/physical behavior are open."
        ),
    },
    "camera": {
        "coverage_classes": ["static_check", "host_firmware_fixture", "physical_pending"],
        "status": "interface_and_wire_fixture; camera hardware qualification pending",
        "boundary": "Interface arithmetic and framed browser fixture are covered; no camera capture or SI proof is claimed.",
    },
    "imu": {
        "coverage_classes": ["static_check", "host_firmware_fixture", "physical_pending"],
        "status": "interface_and_native_fixture; IMU hardware qualification pending",
        "boundary": "Register/interface checks and native raw/status framing are covered; sensor output and mechanical placement remain physical work.",
    },
    "sd": {
        "coverage_classes": ["static_check", "physical_pending"],
        "status": "interface/source evidence; storage hardware qualification pending",
        "boundary": "Pin, footprint, and source evidence are recorded; card insertion, signal integrity, filesystem endurance, and thermal behavior remain physical work.",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    raw = MANIFEST.read_bytes()
    data = json.loads(raw)
    components = data.get("components")
    if not isinstance(components, list) or len(components) != 561:
        raise ValueError(f"expected 561 components, got {len(components) if isinstance(components, list) else 'non-list'}")
    refs = [p.get("ref") for p in components]
    designators = [p.get("designator") for p in components]
    if any(not isinstance(x, str) or not x for x in refs + designators):
        raise ValueError("every component needs a non-empty ref and designator")
    if len(set(refs)) != len(refs) or len(set(designators)) != len(designators):
        raise ValueError("component refs and designators must each be unique")
    expected = {"tactile": 343, "power": 161, "camera": 37, "imu": 5, "sd": 15}
    counts = Counter(p.get("subsystem") for p in components)
    if dict(counts) != expected:
        raise ValueError(f"subsystem counts changed: {dict(counts)} != {expected}")
    return data, components, hashlib.sha256(raw).hexdigest()


def evidence_info(paths):
    info = []
    for rel in paths:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        info.append({"path": rel, "sha256": sha256(path), "bytes": path.stat().st_size})
    return info


def blocker_info():
    remaining_rel = "hardware/glove-v4/electrical/remaining-nets.json"
    routing_rel = "hardware/glove-v4/electrical/routing-progress.json"
    remaining = json.loads((ROOT / remaining_rel).read_text())
    routing = json.loads((ROOT / routing_rel).read_text())
    open_count = remaining.get("open_count")
    if not isinstance(open_count,int) or routing.get("unconnected_items") != open_count:
        raise ValueError("routing evidence disagrees on open connections")
    board=ROOT/"hardware/glove-v4/electrical/glove-v4-routing-candidate.kicad_pcb"
    if sha256(board)!=routing["candidate_sha256"]:raise ValueError("routing board hash mismatch")
    if sha256(MANIFEST)!=routing["components_sha256"]:raise ValueError("routing component source hash mismatch")
    clearance=json.loads((ROOT/"hardware/glove-v4/enclosure/clearance-report.json").read_text())
    mechanics_current=clearance["placement_sha256"]==sha256(ROOT/"hardware/glove-v4/electrical/placement.json")
    return {
        "requested_size": {
            "status":"blocking_first_article_order", "evidence":["hardware/glove-v4/enclosure/compact-size-options.md","hardware/glove-v4/system-contract.json"],
            "detail":"Current assembly 112 × 105.6 × 47.1 mm and estimated 218.2–233.2 g before textile/harness exceed the preferred 50.8 × 38.1 mm footprint. A compact redesign or explicitly accepted dimensioned alternative is required; CAD clearance alone does not close this requirement."
        },
        "landed_cost_and_delivery": {
            "status":"blocking_first_article_order", "evidence":["hardware/glove-v4/procurement/cost-status.md","hardware/glove-v4/procurement/bom-source-plan.csv"],
            "detail":"The requested $150–200 complete one-glove budget is unclosed. Exact assembled/printed/harness/sensor/battery cost, minimum quantities, shipping, VAT and delivery dates need a complete current quote; partial component subtotals do not satisfy it."
        },
        "continuous_runtime": {
            "status":"design_margin_and_delivery_blocker", "evidence":["hardware/glove-v4/verification/energy-budget.json","hardware/glove-v4/guide/factory-record-template.json"],
            "detail":"The conservative 6.019 h calculation leaves about 1.16 minutes over the six-hour target. Changes to electronics/thermal design must update the budget. Delivery requires six-hour simultaneous camera/tactile/IMU/storage operation with recorded temperature, current, capacity and drop counters."
        },
        "physical_and_demo_acceptance": {
            "status":"required_for_tested_delivery", "evidence":["hardware/glove-v4/guide/factory-flash-and-acceptance.md","hardware/glove-v4/guide/factory-record-template.json","hardware/glove-v4/README.md"],
            "detail":"First-article signal/calibration, camera, IMU, storage, radio, harness and wearable-fit checks remain unmeasured. The current reference hand mesh/contact display does not establish finger joint angles, precise hidden-hand position or calibrated roughness; the requested tracking/texture demo needs its own measured acceptance evidence."
        },
        "routing_open_items": {
            "status": "blocking",
            "open_count": open_count,
            "evidence": [remaining_rel, routing_rel, "hardware/glove-v4/electrical/routing-candidate.drc.txt"],
            "detail": f"{open_count} unconnected items remain; the routing candidate DRC includes USB-net/pair work in the blocker scope.",
        },
        "mechanical_revision": {"status":"current_nominal_geometry" if mechanics_current else "recheck_required", "evidence":["hardware/glove-v4/enclosure/clearance-report.json"], "detail":"Clearance evidence matches current component placement." if mechanics_current else "Published clearance result applies to an earlier component placement; rerun before release."},
        "coupled_analog": {"status":"unresolved_solver", "evidence":["hardware/glove-v4/verification/coupled-analog/results.json"], "detail":"One complete conditioned63-amplifier native diagnostic; isolated tightening of gmin or abstol fails, so numerical qualification remains open."},
        "rail_finite_impedance": {
            "status": "ongoing",
            "evidence": [
                "hardware/glove-v4/power/simulation/latest-runs.json",
                "hardware/glove-v4/power/simulation/buck-results.json",
            ],
            "detail": "A corrected native buck run is recorded; full finite-impedance rail qualification remains open.",
        },
        "usb_high_current_path": {
            "status":"blocking", "evidence":["hardware/glove-v4/verification/routing-proposal20/usb-power-path.json"],
            "detail":"The unapplied20-open candidate improves USB inlet routing. Its actual U32 OUT and U42 VBUS surface escapes still need width/thermal correction; plane-only resistance was insufficient evidence. Canonical board remains24-open."
        },
        "shutdown_fault_paths": {
            "status": "blocking",
            "evidence": ["firmware/tactile_v4/main/app.cpp", "firmware/tactile_v4/main/storage.cpp"],
            "detail": "Lost-source latch, bounded camera queue and owner-acknowledged checked shutdown are built/tested. Permanent peripheral/control-bus faults still need independent reset/power-off hardware; current firmware holds shutdown rather than asserting successful sleep.",
        },
        "thermal": {
            "status": "blocking",
            "evidence": ["hardware/glove-v4/verification/thermal-screen/results.json"],
            "detail": "Thermal-resistance sensitivity calculations exceed contact/pack screening targets; the buffered temperature-readout and outward heat-path proposals have local evidence plus a native-tested isolated temperature policy; circuit and shutdown integration remain unapplied and continuous wear remains unqualified.",
        },
    }


def make_report():
    manifest, components, manifest_sha = load_manifest()
    evidence = {name: evidence_info(paths) for name, paths in EVIDENCE.items()}
    rows = []
    for p in components:
        block = p["subsystem"]
        spec = BLOCKS[block]
        rows.append(
            {
                "ref": p["ref"],
                "designator": p["designator"],
                "mpn": p.get("mpn"),
                "subsystem": block,
                "block_coverage_classes": spec["coverage_classes"],
                "block_coverage_status": spec["status"],
                "individual_dynamic_model_claim": "Five completed differential ADC cases; U_BANK1 uses one representative amplifier section." if p["ref"] in {"U_BANK1","U_ADC_DRV","U_ADC_NEG","R_ADC_ISO","R_ADC_NEG_ISO","C_ADC_BUCKET","C_ADC_NEG_BUCKET"} else "Block evidence only; no individual complete dynamic simulation claim.",
                "block_evidence_paths": [e["path"] for e in evidence[block]],
            }
        )
    # Keep the component order deterministic even if a future generator changes it.
    rows.sort(key=lambda x: (x["subsystem"], x["ref"]))
    block_summary = {}
    for name in BLOCKS:
        members = [p for p in components if p["subsystem"] == name]
        block_summary[name] = {
            "component_count": len(members),
            "coverage_classes": BLOCKS[name]["coverage_classes"],
            "status": BLOCKS[name]["status"],
            "boundary": BLOCKS[name]["boundary"],
            "evidence": evidence[name],
        }
    report = {
        "schema": 2,
        "full_hardware_verified": False,
        "manufacturing_release": False,
        "generated_by": "hardware/glove-v4/verification/build_hardware_coverage_matrix.py",
        "claim_boundary": (
            "This is a component inventory and evidence map. Static checks, electrical "
            "simulation/model proxies, host/firmware fixtures, and physical qualification "
            "are separate classes; coverage here does not claim comprehensive actual-hardware simulation."
        ),
        "manifest": {
            "path": "hardware/glove-v4/electrical/components.json",
            "sha256": manifest_sha,
            "component_count": len(components),
            "subsystem_counts": dict(sorted(Counter(p["subsystem"] for p in components).items())),
        },
        "generator_sha256": sha256(Path(__file__).resolve()),
        "blocks": block_summary,
        "components": rows,
        "blockers": blocker_info(),
    }
    for blocker in report["blockers"].values():
        for rel in blocker["evidence"]:
            if not (ROOT/rel).is_file():raise FileNotFoundError(rel)
    return report


def markdown(report):
    lines = [
        "# V4 hardware coverage matrix",
        "",
        "Generated from the 561-row V4 component manifest. This is an evidence map: static checks, electrical simulation/model proxies, host/firmware fixtures, and physical qualification are separate classes. It does not claim comprehensive actual-hardware simulation.",
        "",
        f"Manifest SHA256: `{report['manifest']['sha256']}`",
        f"Generator SHA256: `{report['generator_sha256']}`",
        "",
        "## Coverage by block",
        "",
        "| Block | Components | Evidence classes | Current status |",
        "|---|---:|---|---|",
    ]
    for name, block in report["blocks"].items():
        lines.append(f"| {name} | {block['component_count']} | {', '.join(block['coverage_classes'])} | {block['status']} |")
    lines += ["", "## Block boundaries", ""]
    for name, block in report["blocks"].items():
        lines += [f"**{name} ({block['component_count']})** — {block['boundary']}", ""]
    lines += ["## Open release blockers", "", "Design/quote gates apply before a first-article order. Measured physical acceptance applies before delivery as a tested working glove; it cannot be completed before the first unit exists.", "", "| Blocker | Status | Evidence / detail |", "|---|---|---|"]
    for name, blocker in report["blockers"].items():
        evidence = ", ".join(blocker["evidence"]) if blocker["evidence"] else "none"
        lines.append(f"| {name} | {blocker['status']} | {blocker['detail']} Evidence: {evidence} |")
    lines += [
        "",
        "## Reproduction",
        "",
        "Run `python3 hardware/glove-v4/verification/build_hardware_coverage_matrix.py` from the repository root. The script checks the manifest count, unique refs/designators, exact subsystem counts, evidence existence, and the current routing source/board hashes and clearance-placement correspondence before writing the JSON and Markdown reports.",
        "",
        "The full per-component one-to-one inventory, evidence paths, and SHA256 values are in `hardware/glove-v4/verification/hardware-coverage-matrix.json`.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    report = make_report()
    JSON_OUT.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    MD_OUT.write_text(markdown(report))
    print(f"wrote {JSON_OUT} and {MD_OUT}: {len(report['components'])} components")
