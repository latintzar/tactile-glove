#!/usr/bin/env python3
"""Recheck native diagnostics. A completed relaxed run is not numerical qualification."""
import gzip, hashlib, importlib.util, json, re
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
RUNNER=P.parents[1]/'run.py'
spec=importlib.util.spec_from_file_location('coupled',RUNNER)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=[]
for name in ['conditioned','lower_gmin','lower_abstol','tight','tight_gmin9']:
    d=P/name;deck=(d/'circuit.cir').read_text();log=gzip.decompress((d/'run.log.gz').read_bytes()).decode()
    options=next(l for l in deck.splitlines() if l.startswith('.options '))
    default,meta=m.generate('single_positive')
    # Exact generated canonical circuit; only the solver option line may differ.
    strip=lambda s: '\n'.join(l for l in s.splitlines() if not l.startswith('.options '))
    assert strip(deck)==strip(default),name
    errors=[l for l in log.splitlines() if re.search(r'aborted|timestep too small|error:|fatal|singular matrix|no convergence',l,re.I)]
    ends=re.findall(r'actual_simulation_end\s*=\s*([-+0-9.eE]+)',log)
    end=float(ends[-1]) if ends else None
    complete=not errors and end is not None and abs(end-.135)<1e-9 and bool(re.search(r'ngspice-\S+ done',log))
    row={'case':name,'solver_options':options,'complete_native_trace':complete,'native_end_s':end,
         'errors':errors[-8:],'canonical_circuit_unchanged':True,
         'artifacts_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(d.iterdir()) if f.name in ['circuit.cir','run.log.gz','waveform.dat.gz']}}
    if complete:
        m.analyze_waveform(d/'waveform.dat.gz',meta,'single_positive',d/'display.csv')
        (d/'display.csv.gz').write_bytes(gzip.compress((d/'display.csv').read_bytes(),mtime=0))
        (d/'display.csv').unlink()
        for key in ['samples','baseline_V','pulse_differential_peak_V','quiet_to_active_peak_ratio','pressure_step_vexc_min_V','pressure_step_idle_differential_max_V','pressure_step_vexc_final_V','recovery_differential_residual_V']:
            row[key]=meta[key]
        row['waveform_uncompressed_sha256']=hashlib.sha256(gzip.decompress((d/'waveform.dat.gz').read_bytes())).hexdigest()
    rows.append(row)
assert sum(r['complete_native_trace'] for r in rows)==1
out={'status':'diagnostic_complete; tolerance convergence unestablished','qualified_coupled_cases':0,
     'completed_native_diagnostics':1,'canonical_sha256':meta['canonical_sha256'],
     'runner_sha256':hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
     'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
     'cases':rows,'limits':['The successful native trace needs both1nA absolute tolerance and1nS gmin. Tightening either alone prevents completion.',
         'No converged sensitivity comparison exists; resulting voltage amplitudes are diagnostic only.',
         'Ideal3.3V rail and3V reference; typical vendor models at27C; no mux/ADC sampling/harness parasitic extraction.',
         'Twenty1Gohm-to1ohm contact transitions bound the excitation load; they do not model observed glove behavior.']}
(P/'results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['status','qualified_coupled_cases','completed_native_diagnostics']}))
