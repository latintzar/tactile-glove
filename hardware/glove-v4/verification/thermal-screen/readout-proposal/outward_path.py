#!/usr/bin/env python3
"""Sensitivity to an added electronics-to-outward-shell path; no CAD claim."""
import sys,json,itertools,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import screen as s
base=s.residual_for
G=0
def extra(temps,heat,ambient,boundary,params):
    res,out,phantom=base(temps,heat,ambient,boundary,params)
    q=G*(temps[0]-temps[2]);res[0]+=q;res[2]-=q
    return res,out,phantom
s.residual_for=extra
r=json.loads((HERE.parent/'results.json').read_text())
profiles=list(itertools.product([3,8],[.75,.95],[.127,.30],[.03,.10],[.45,.85],[.1,3]))
rows=[]
for G,mode,ambient in itertools.product([0,.1,.2,.3],['recording_sustained','charging_and_recording_sustained'],[25,35,40]):
    p=r['power_ranges'][mode];heats=list(itertools.product(p['electronics_heat_w'],p['pack_heat_w']))
    vals=[s.thermal(h,ambient,'34C_phantom_R15',v)[0] for h,v in itertools.product(heats,profiles)]
    rows.append({'additional_conductance_W_K':G,'additional_path_R_K_W':1/G if G else None,'mode':mode,'ambient_C':ambient,'temperature_range_C':{n:[min(v[i] for v in vals),max(v[i] for v in vals)] for i,n in enumerate(s.NAMES)}})
capacity={str(t):{str(a):[s.A_EXPOSED*(h*(t-a)+eps*s.SIGMA*((t+273.15)**4-(a+273.15)**4)) for h,eps in [(3,.75),(8,.95)]] for a in [25,35,40]} for t in [40,45,50]}
out={'status':'unapplied conductance target; no designed/validated heat spreader','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'screen_sha256':hashlib.sha256((HERE.parent/'screen.py').read_bytes()).hexdigest(),'thermal_results_sha256':hashlib.sha256((HERE.parent/'results.json').read_bytes()).hexdigest(),'extra_path':'electronics_mean to exposed_shell_mean only, no direct battery or base bridge','cases':rows,'outside_only_rejection_W_by_surface_and_ambient_C':capacity,'target':'At least0.2W/K added electronics-to-outer-shell conductance (<=5K/W); test local component/skin gradients separately. This target alone does not meet40C base at35/40C in all modeled corners.'}
(HERE/'outward-path-results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'sustained':[x for x in rows if x['mode']=='recording_sustained' and x['additional_conductance_W_K'] in [0,.2]],'outside_only_rejection_W':capacity},indent=2))
