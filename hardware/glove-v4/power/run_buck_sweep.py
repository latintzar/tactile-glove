#!/usr/bin/env python3
"""Bounded original TI model; reject ngspice errors even when its exit code is 0."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import os
import re
import shutil
import shlex
import subprocess
import time
import uuid

P = Path(__file__).resolve().parent
S = P / 'simulation'
CASES = ['buck', 'buck_3p0_1p2', 'buck_3p7_1p2', 'buck_4p4_1p2',
         'buck_3p7_1p8', 'buck_startup', 'buck_corrected60u',
         'buck_path190m_start', 'buck_path190m_low',
         'buck_path_network_start', 'buck_path_network_low',
         'buck_path_operating_4p2', 'buck_path_operating_3p7', 'buck_path_operating_3p2',
         'buck_path_operating_3p7_klu', 'buck_path_network_start_klu']
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


def rewrite_top_level_includes(text, source_parent):
    """Make staged top-level model includes independent of the attempt cwd."""
    lines=[]
    pattern=re.compile(r'^(\s*\.include\s+)(?:"([^"]+)"|\'([^\']+)\'|(\S+))(.*)$', re.IGNORECASE)
    for line in text.splitlines(keepends=True):
        match=pattern.match(line.rstrip('\r\n'))
        if not match:
            lines.append(line)
            continue
        token=match[2] or match[3] or match[4]
        include_path=Path(token)
        if not include_path.is_absolute():
            include_path=(source_parent/include_path).resolve()
        suffix=match[5]
        newline=line[len(line.rstrip('\r\n')):]
        lines.append(f'{match[1]}"{include_path}"{suffix}{newline}')
    return ''.join(lines)


def assess(log, returncode, expected_end_s):
    """The native time vector must reach the end before linearize pads it."""
    error_patterns = [
        r'simulation\(s\) aborted', r'timestep too small', r'\berror\s*:',
        r'\bfatal\b', r'singular matrix', r'no convergence',
        r'convergence failed', r'cannot find', r'unknown parameter',
    ]
    errors = [line.strip() for line in log.splitlines()
              if any(re.search(pattern, line, re.IGNORECASE)
                     for pattern in error_patterns)]
    times = re.findall(r'actual_simulation_end\s*=\s*([-+0-9.eE]+)', log)
    try:
        actual = float(times[-1]) if times else None
    except ValueError:
        actual = None
        errors.append('Invalid actual_simulation_end marker')
    completion_marker = bool(re.search(
        r'^\s*ngspice-\S+\s+done\s*$', log,
        re.MULTILINE | re.IGNORECASE))
    complete = (returncode == 0 and not errors and completion_marker
                and actual is not None
                and actual >= expected_end_s * (1 - 1e-6))
    return {
        'simulator_returncode': returncode,
        'analysis_complete': complete,
        'actual_native_end_s': actual,
        'expected_end_s': expected_end_s,
        'completion_marker': completion_marker,
        'simulation_errors': errors,
    }


def validate_waveform(path, expected_end_s, expected_step_s, native_end_s=None, expected_columns=None):
    """Validate exported rows without rejecting physically valid zero-valued signals."""
    errors = []
    if not path.exists():
        return {'valid': False, 'rows': 0, 'expected_rows': None,
                'last_time_s': None, 'all_zero_tail_rows': 0,
                'errors': ['Waveform export is missing']}
    rows = []
    try:
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            values = [float(value) for value in line.split()]
            finite = all(value == value and abs(value) != float('inf')
                         for value in values)
            if not values or len(values) < 2 or not finite:
                errors.append(f'Invalid waveform row {line_number}')
            rows.append(values)
    except (OSError, ValueError) as exc:
        errors.append(f'Cannot parse waveform: {exc}')
    if not rows:
        errors.append('Waveform export is empty')
    expected_rows = round(expected_end_s / expected_step_s) + 1
    last_time = rows[-1][0] if rows and rows[-1] else None
    if expected_columns is not None and any(len(row) != expected_columns for row in rows):
        errors.append(f'Unexpected waveform column count; expected {expected_columns}')
    if rows and any(len(row) != len(rows[0]) for row in rows):
        errors.append('Waveform rows have inconsistent column counts')
    if rows and len(rows) != expected_rows:
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
    # A zero-valued physical signal is valid. A zero tail is diagnostic only
    # when the native simulation itself stopped early; the native marker remains
    # the completion gate.
    if (native_end_s is not None
            and native_end_s < expected_end_s * (1 - 1e-6)
            and zero_tail):
        errors.append(f'Zero-filled tail follows incomplete native run ({zero_tail} rows)')
    return {
        'valid': not errors,
        'rows': len(rows),
        'expected_rows': expected_rows,
        'last_time_s': last_time,
        'all_zero_tail_rows': zero_tail,
        'errors': errors,
    }


def atomic_copy(source, destination):
    temporary = destination.with_name(destination.name + '.candidate-' + uuid.uuid4().hex)
    shutil.copyfile(source, temporary)
    os.replace(temporary, destination)


def atomic_write(path, content):
    temporary = path.with_name(path.name + '.candidate-' + uuid.uuid4().hex)
    temporary.write_text(content)
    os.replace(temporary, path)


def unique_case_names(names):
    if len(names) != len(set(names)):
        raise ValueError('Duplicate --case values would race on shared output names')
    return names


def main():
    pa = argparse.ArgumentParser()
    pa.add_argument('--ngspice', default='/tmp/glove-eda-runtime/usr/bin/ngspice')
    pa.add_argument('--cm-dir', default='/tmp/glove-eda-runtime/usr/lib/x86_64-linux-gnu/ngspice')
    pa.add_argument('--sudo', action='store_true')
    pa.add_argument('--case', action='append', choices=CASES)
    pa.add_argument('--timeout-seconds', type=int, default=600)
    a = pa.parse_args()
    if not 1 <= a.timeout_seconds <= 1800:
        pa.error('timeout must be 1..1800 seconds')
    (S / 'scripts').mkdir(exist_ok=True)
    (S / 'scripts' / 'spinit').write_text(
        'set ngbehavior=ps\n' + ''.join(
            f'codemodel {a.cm_dir}/{f}\n' for f in
            ['analog.cm', 'digital.cm', 'spice2poly.cm', 'xtradev.cm',
             'xtraevt.cm', 'table.cm']))
    names = unique_case_names(a.case or CASES)
    attempts = S / '.attempts'
    attempts.mkdir(exist_ok=True)

    def run(name):
        attempt = attempts / (name + '-' + time.strftime('%Y%m%dT%H%M%S')
                              + '-' + uuid.uuid4().hex[:8])
        attempt.mkdir()
        deck = S / (name + '.cir')
        result = {'name': name,
                  'attempt_directory': str(attempt.relative_to(S)),
                  'analysis_complete': False,
                  'simulation_errors': []}
        try:
            original = deck.read_text()
            step, end = deck_timing(deck)
            expected_columns = deck_expected_columns(deck)
            # Instrument only the attempt deck; the source deck remains unchanged.
            code = rewrite_top_level_includes(original, deck.parent).replace(
                'linearize ',
                'let actual_simulation_end = time[length(time)-1]\n'
                'print actual_simulation_end\nlinearize ', 1)
            active = attempt / (name + '.executing.cir')
            active.write_text(code)
            waveform = attempt / (name + '.txt')
            logpath = attempt / (name + '.log')
            cmd = ['timeout', str(a.timeout_seconds), a.ngspice, '-b', active.name]
            env = dict(os.environ, SPICE_SCRIPTS=str(S / 'scripts'))
            if a.sudo:
                cmd = ['sudo', '-n', 'env', 'SPICE_SCRIPTS=' + env['SPICE_SCRIPTS'],
                       'LD_LIBRARY_PATH=' + env.get('LD_LIBRARY_PATH', '')] + cmd
            start = time.time()
            with logpath.open('w') as f:
                proc = subprocess.run(cmd, cwd=attempt, env=env,
                                      stdout=f, stderr=subprocess.STDOUT)
            log = logpath.read_text(errors='replace')
            result.update({
                'seconds': round(time.time() - start, 3),
                **assess(log, proc.returncode, end),
                'expected_step_s': step,
                'expected_columns': expected_columns,
                'deck_sha256': hashlib.sha256(deck.read_bytes()).hexdigest(),
                'executed_deck_sha256': hashlib.sha256(code.encode()).hexdigest(),
                'log_sha256': hashlib.sha256(logpath.read_bytes()).hexdigest(),
                'waveform_sha256': (hashlib.sha256(waveform.read_bytes()).hexdigest()
                                    if waveform.exists() else None),
            })
            waveform_check = validate_waveform(
                waveform, end, step, result.get('actual_native_end_s'), expected_columns)
            result['waveform_validation'] = waveform_check
            result['analysis_complete'] = (result['analysis_complete']
                                           and waveform_check['valid'])
            if not result['analysis_complete']:
                result['simulation_errors'].extend(waveform_check['errors'])
            atomic_write(attempt / (name + '.run.json'),
                         json.dumps(result, indent=2) + '\n')
            # Preserve existing evidence on failure; publish only a verified run.
            if result['analysis_complete']:
                atomic_copy(waveform, S / (name + '.txt'))
                atomic_copy(logpath, S / (name + '.log'))
                atomic_copy(attempt / (name + '.run.json'), S / (name + '.run.json'))
            return result
        except Exception as exc:
            result['simulation_errors'].append(f'{type(exc).__name__}: {exc}')
            atomic_write(attempt / (name + '.run.json'),
                         json.dumps(result, indent=2) + '\n')
            return result

    with ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(run, names))
    atomic_write(S / 'latest-runs.json', json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    return 0 if all(r['analysis_complete'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
