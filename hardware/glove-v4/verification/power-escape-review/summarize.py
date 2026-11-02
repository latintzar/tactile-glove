"""Summarize exact-board geometry and finite DC estimates; not thermal qualification.
Usage: summarize.py BOARD OUTPUT_DIRECTORY (contains the regenerated plane reports).
"""
from pathlib import Path
import collections
import hashlib
import json
import math
import re
import sys
import pcbnew as k

board_path = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
b = k.LoadBoard(str(board_path))
board_hash = sha(board_path)
xy = lambda p: (k.ToMM(p.x), k.ToMM(p.y))
review_dir = Path(__file__).resolve().parent
root = review_dir.parents[3]
components_path = root / 'hardware/glove-v4/electrical/components.json'
components = json.loads(components_path.read_text())['components']
fps = {f.GetReference(): f for f in b.GetFootprints()}
assert set(fps) == {c['designator'] for c in components}
for component in components:
    pins = {}
    for pad in fps[component['designator']].Pads():
        pins.setdefault(pad.GetNumber(), set()).add(pad.GetNetname())
    for number, net in component['pins'].items():
        assert pins.get(number) == {'' if net == 'NC' else net}, (component['designator'], number)

full = json.loads((out / 'power-corridor-calculations.json').read_text())
assert full['board_sha256'] == board_hash
assert all(p['converged_5percent'] for p in full['plane_models'].values())
inlet = [json.loads((out / f'vbus-inlet-{step}.json').read_text()) for step in [.1, .075]]
assert all(p['board_sha256'] == board_hash for p in inlet)
inlet_change = abs(inlet[0]['resistance_at30um_ohm'] / inlet[1]['resistance_at30um_ohm'] - 1)
assert inlet_change <= .05
rho = 1.724e-8 * (1 + .00393 * 30)
main_current = 22980 / ((1 / (1 / 71.5 + 1 / 30.9)) * .999)**.94 / 1000
total_current = main_current + 66 / .999**1.072 / 1000 + .00026
planes = {
    'USB_VBUS': max(p['resistance_at30um_ohm'] for p in inlet) * 30 / 24 * 1.05,
    'USB_CHARGER_IN': full['plane_models']['usb']['resistance_30um_ohm'] * 30 / 24 * 1.05,
}
surfaces = []
def surface(name, length, width):
    d = {'name': name, 'length_mm': length, 'width_mm': width,
         'resistance_ohm': rho / 28e-6 * length / width}
    surfaces.append(d)
    return d

def native_route(points, width):
    result = []
    for a, end in zip(points, points[1:]):
        matches = [t for t in b.GetTracks() if t.Type() != k.PCB_VIA_T
                   and t.GetNetname() == 'USB_CHARGER_IN' and t.GetLayer() == k.F_Cu
                   and math.dist(xy(t.GetStart()), a) < 1e-5
                   and math.dist(xy(t.GetEnd()), end) < 1e-5
                   and abs(k.ToMM(t.GetWidth()) - width) < 1e-5]
        assert len(matches) == 1, (a, end, width)
        result.append(matches[0])
    return result

route = json.loads((review_dir / 'output-route.json').read_text())
tracks = native_route(route, .6)
native_route([(14.025, 68.25), (13.875, 68.45)], .28)
assert xy(next(p for p in fps['U32'].Pads() if p.GetNumber() == '6').GetPosition()) == tuple(route[0])
assert xy(next(p for p in fps['U42'].Pads() if p.GetNumber() == '24').GetPosition()) == (14.025, 68.25)
surface('J11 VBUS pad spreading; conservatively all current in one pad', .725, .6)
surface('U32 IN pad spreading to existing via', math.dist((87.55, 58.6375), (87.3, 58.6)), .25)
u32 = surface('U32 OUT seven native F.Cu segments', sum(k.ToMM(t.GetLength()) for t in tracks), .6)
surface('Entire branch to second POWER_A source via', math.dist((85.1229, 57.5659), (85.0229, 58.1659)), .6)
u42 = surface('U42 pin24 VBUS to new plane via', .25, .28)
barrels = []
for name, point, depth, drill, net in [
    ('J11 inlet', (92.015, 51.55), .8805, .3, 'USB_VBUS'),
    ('U32 IN', (87.3, 58.6), .8805, .3, 'USB_VBUS'),
    ('U32 OUT', (85.1229, 57.5659), .7205, .3, 'USB_CHARGER_IN'),
    ('U42 VBUS', (13.875, 68.45), .7205, .2, 'USB_CHARGER_IN'),
]:
    vias = [v for v in b.GetTracks() if v.Type() == k.PCB_VIA_T and v.GetNetname() == net
            and math.dist(xy(v.GetPosition()), point) < 1e-5]
    assert len(vias) == 1 and abs(k.ToMM(vias[0].GetDrillValue()) - drill) < 1e-5
    length = depth * 1.76 / 1.636
    resistance = rho * length / 1000 / (math.pi * (drill + .015) / 1000 * 15e-6)
    barrels.append({'name': name, 'xy_mm': point, 'drill_mm': drill, 'barrel_length_mm': length,
                    'resistance_ohm': resistance, 'one_via_carries_full_current': True})
resistance = sum(planes.values()) + sum(x['resistance_ohm'] for x in surfaces + barrels)
width_required = (main_current / (.048 * 10**.44))**(1 / .725) / (28 / 25.4) * .0254
old = json.loads((review_dir.parent / 'routing-proposal20/usb-power-path.json').read_text())
drc = board_path.with_suffix('.drc.txt').read_text()
counts = dict(collections.Counter(re.findall(r'^\[(.*?)\]', drc, re.M)))
physical_errors = sum('Severity: error' in x and not x.startswith('unconnected_items') for x in drc.split('\n['))
assert physical_errors == 0 and counts['unconnected_items'] == 20
report = {
    'board_sha256': board_hash, 'component_manifest_sha256': sha(components_path),
    'component_count': len(components), 'canonical_pin_map_mismatches': 0,
    'physical_drc_errors': physical_errors, 'remaining_connections': counts['unconnected_items'],
    'drc_counts': counts, 'status': 'unapplied engineering candidate', 'manufacturing_ready': False,
    'scope': 'USB high-current positive copper. Full USB ground return, recovery branch and enclosure temperature remain outside this calculation.',
    'temperature_C': 50, 'copper_assumptions_um': {'outer': 28, 'inner': 24, 'barrel_plating': 15},
    'main_branch_current_max_A': main_current, 'total_input_current_A': total_current,
    'plane_estimates_ohm': planes, 'surface_estimates': surfaces, 'barrel_estimates': barrels,
    'positive_copper_estimate_ohm': resistance,
    'at_total_input_current': {'drop_V': total_current * resistance, 'loss_W': total_current**2 * resistance},
    'previous_candidate': {'board_sha256': old['board_sha256'], 'positive_copper_estimate_ohm': old['positive_copper_resistance_bound_ohm']},
    'calculated_resistance_reduction_percent': 100 * (1 - resistance / old['positive_copper_resistance_bound_ohm']),
    'U32_output': {'length_mm': u32['length_mm'], 'width_mm': .6, 'required_width_mm': width_required,
                   'long_conductor_width_screen_pass': .6 >= width_required},
    'U42_input': {'pin': 24, 'fanout_length_mm': .25, 'fanout_width_mm': .28,
                 'via_diameter_mm': .4, 'via_drill_mm': .2, 'filled_capped_planarized_process_required': True,
                 'short_fanout_loss_at_main_current_W': main_current**2 * u42['resistance_ohm'],
                 'via_loss_at_main_current_W': main_current**2 * barrels[-1]['resistance_ohm']},
    'inlet_mesh_relative_change': inlet_change, 'battery_plus_return_ohm': full['battery_plus_return_total_calculated_ohm'],
    'battery_copper_allocation_ohm': .015,
    'limitations': [
        'Minimum copper/plating values are engineering assumptions requiring fabricator confirmation.',
        'A DC sheet and IPC long-conductor width screen do not establish local or enclosed temperature rise.',
        'Terminal contacts are idealized disks; grids are converged to 5 percent and a 5 percent mesh margin is applied.',
        'The U42 fanout is a short package escape; the long-conductor formula is not an ampacity proof for it.',
        'TPS2553 loss, charger DPM, cable/connector losses, inrush and battery/harness variation remain in the full power qualification.',
        'Canonical board promotion awaits the existing approval; this archive is not an ordering package.',
    ],
}
(out / 'usb-power-summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['board_sha256', 'positive_copper_estimate_ohm', 'calculated_resistance_reduction_percent', 'battery_plus_return_ohm', 'remaining_connections']}, indent=2))
