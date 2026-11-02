#!/usr/bin/env python3
"""Analyze saved ngspice waveforms; native execution requires matched runner metadata."""
from pathlib import Path
import hashlib
import json
import math
import os
import re
import shlex
import uuid
from run_buck_sweep import assess

P = Path(__file__).resolve().parent
S = P / 'simulation'
CASES = ['buck', 'buck_3p0_1p2', 'buck_3p7_1p2', 'buck_4p4_1p2',
         'buck_3p7_1p8', 'buck_startup', 'buck_corrected60u']
TIME_SCALE = {'': 1, 'm': 1e-3, 'u': 1e-6, 'n': 1e-9, 'p': 1e-12}


def parse_time(value):
    match = re.fullmatch(
        r'([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)([munp]?)',
        value.strip())
    if not match:
        raise ValueError(f'Invalid ngspice time value: {value}')
    return float(match[1]) * TIME_SCALE[match[2]]


def deck_timing(deck):
    for line in deck.read_text().splitlines():
        match = re.match(r'^\s*tran\s+(\S+)\s+(\S+)', line, re.IGNORECASE)
        if match:
            return parse_time(match[1]), parse_time(match[2])
    raise ValueError(f'Missing bounded transient command in {deck.name}')


def deck_expected_columns(deck):
    for line in deck.read_text().splitlines():
        match = re.match(r'^\s*wrdata\s+\S+\s+(.+)$', line, re.IGNORECASE)
        if match:
            traces = shlex.split(match[1])
            if traces:
                return 2 * len(traces)
    raise ValueError(f'Missing bounded wrdata command in {deck.name}')


def read_waveform(path, expected_end_s, expected_step_s, expected_columns):
    errors = []
    rows = []
    try:
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            values = [float(value) for value in line.split()]
            finite = all(math.isfinite(value) for value in values)
            if not values or len(values) < 2 or not finite:
                errors.append(f'Invalid waveform row {line_number}')
            rows.append(values)
    except (OSError, ValueError) as exc:
        errors.append(f'Cannot parse waveform: {exc}')
    if not rows:
        errors.append('Waveform export is empty')
    expected_rows = round(expected_end_s / expected_step_s) + 1
    last_time = rows[-1][0] if rows and rows[-1] else None
    if any(len(row) != expected_columns for row in rows):
        errors.append(f'Unexpected waveform column count; expected {expected_columns}')
    if rows and any(len(row) != len(rows[0]) for row in rows):
        errors.append('Waveform rows have inconsistent column counts')
    if len(rows) != expected_rows:
        errors.append(f'Unexpected waveform row count {len(rows)}; expected {expected_rows}')
    times = [row[0] for row in rows if row]
    if rows and len(times) == len(rows) and any(b <= a for a, b in zip(times, times[1:])):
        errors.append('Waveform time column is not strictly increasing')
    if last_time is not None and last_time < expected_end_s * (1 - 1e-6):
        errors.append('Waveform endpoint is short of the deck endpoint')
    zero_tail = 0
    for row in reversed(rows):
        if len(row) > 1 and all(value == 0.0 for value in row[1:]):
            zero_tail += 1
        else:
            break
    return {
        'rows': len(rows),
        'expected_rows': expected_rows,
        'last_time_s': last_time,
        'all_zero_tail_rows': zero_tail,
        'errors': errors,
        'valid': not errors,
        'data': rows,
    }


def matched_runner_metadata(name, deck_hash, waveform_hash, expected_end_s):
    path = S / (name + '.run.json')
    if not path.exists():
        return False, 'historical waveform; original solver log unavailable'
    try:
        metadata = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return False, f'runner metadata unreadable: {exc}'
    matched = (
        metadata.get('analysis_complete') is True
        and metadata.get('deck_sha256') == deck_hash
        and metadata.get('waveform_sha256') == waveform_hash
        and metadata.get('actual_native_end_s') is not None
        and metadata['actual_native_end_s'] >= expected_end_s * (1 - 1e-6)
    )
    log_path = S / (name + '.log')
    if matched:
        if not log_path.exists() or hashlib.sha256(log_path.read_bytes()).hexdigest() != metadata.get('log_sha256'):
            return False, 'runner native log missing or hash mismatch'
        native = assess(log_path.read_text(errors='replace'), metadata.get('simulator_returncode'), expected_end_s)
        if not native['analysis_complete']:
            return False, 'retained native log does not confirm completion'
        return True, f'validated matched runner metadata and native log: {path.name}'
    return False, 'runner metadata present but does not validate this deck/waveform'


result = []
for name in CASES:
    deck = S / (name + '.cir')
    waveform = S / (name + '.txt')
    deck_hash = hashlib.sha256(deck.read_bytes()).hexdigest()
    waveform_hash = hashlib.sha256(waveform.read_bytes()).hexdigest()
    step, expected_end = deck_timing(deck)
    expected_columns = deck_expected_columns(deck)
    coverage = read_waveform(waveform, expected_end, step, expected_columns)
    rows = coverage.pop('data')
    post = [row for row in rows if row and row[0] >= 350e-6]
    voltage = [row[1] for row in rows if len(row) > 1]
    post_voltage = [row[1] for row in post if len(row) > 1]
    native_verified, execution_evidence = matched_runner_metadata(
        name, deck_hash, waveform_hash, expected_end)
    lo = min(post_voltage) if post_voltage else None
    hi = max(post_voltage) if post_voltage else None
    peak = max(voltage) if voltage else None
    result.append({
        'deck': deck.name,
        'mode': 'forced PWM',
        'startup': 'zero-output softstart' if name == 'buck_startup' else 'prebiased output',
        'samples': coverage['rows'],
        'expected_samples': coverage['expected_rows'],
        'expected_columns': expected_columns,
        'expected_end_s': expected_end,
        'time_end_s': coverage['last_time_s'],
        'complete': coverage['valid'],
        'complete_field_scope': 'saved waveform coverage; native solver completion separately tracked',
        'native_execution_verified': native_verified,
        'execution_evidence': execution_evidence,
        'waveform_validation_errors': coverage['errors'],
        'all_zero_tail_rows': coverage['all_zero_tail_rows'],
        'post350us_min_V': lo,
        'post350us_max_V': hi,
        'whole_run_max_V': peak,
        'old_100mV_droop_60mV_overshoot_allocation_pass': (
            lo is not None and hi is not None and lo >= 3.316 and hi <= 3.476),
        'main_abs_rail_limit_pass': hi is not None and hi < 3.6,
        'waveform_sha256': waveform_hash,
        'deck_sha256': deck_hash,
    })

curves = []
for item in json.loads((P / 'sources/mlcc-dc-bias.json').read_text())['JsonCharaData']:
    for curve in item['charadata']:
        if curve.get('error'):
            continue
        data = [(x[0][0], x[1][0]) for x in curve['data']]
        cap = None
        for (x, y), (xx, yy) in zip(data, data[1:]):
            if x <= 3.6 <= xx:
                cap = y + (yy - y) * (3.6 - x) / (xx - x)
                break
        if cap is not None:
            curves.append({'part': item['partnumber'],
                           'temperature_C': float(curve['tc']),
                           'cap_at3V6_uF': cap})
selected = [x['cap_at3V6_uF'] for x in curves if x['part'].startswith('GRM32')]
bank = 3 * min(selected) * .9 * .8
r = {
    'schema': 2,
    'physical_validation': False,
    'manufacturer_model': 'Unmodified TI SLVMBP8 TPS63070_TRANS.LIB',
    'model_sha256': hashlib.sha256((P / 'models/SLVMBP8/TPS63070_PSPICE_TRANS/TPS63070_TRANS.LIB').read_bytes()).hexdigest(),
    'cases': result,
    'mlcc_typical_curves': curves,
    'selected_bank_after_10pct_tolerance_and20pct_extra_allowance_uF': bank,
    'corrected_model_effective_C_uF': 60,
    'capacitance_design_check_pass': bank > 60,
    'mode_policy': 'Forced PWM for startup and all camera/SD/tactile activity. Enter PFM only after rails are off and output has settled.',
    'revised_design_allocation': {
        'PWM_droop_V': .12,
        'PWM_overshoot_V': .1,
        'PFM_standby_overshoot_V': .06,
        'basis': '100mV/60mV preliminary allocation failed at the 1A PWM load step. Revised allocation uses measured model extrema plus margin and independent datasheet voltage limits; the old failures are retained above.'},
    'limits': [
        'Historical seven cases retain complete finite waveforms and matching source hashes, but native execution is unproven unless matched runner metadata is present.',
        'Model is typical, with ideal stiff VIN and no PCB parasitics. It does not establish worst-case device transient performance.',
        'DC-bias curves are manufacturer typical characterization, not guaranteed production capacitance. The 20% extra factor is an engineering allowance.',
        'PFM transition and charger/current-limiter loop interaction need physical testing.',
        'Corrected 60uF run repeats the worst observed 3.7V/1.2uH case; other corners used the more severe 40uF load.',
        'Prebiased cases test load response; only buck_startup tests startup from zero.'
    ]
}
temporary = S / ('buck-results.json.candidate-' + uuid.uuid4().hex)
temporary.write_text(json.dumps(r, indent=2) + '\n')
os.replace(temporary, S / 'buck-results.json')
print(json.dumps({'cases': len(result), 'cap_bank_uF': bank,
                  'native_verified': sum(x['native_execution_verified'] for x in result)}))
