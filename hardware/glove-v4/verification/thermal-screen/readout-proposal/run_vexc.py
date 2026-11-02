from pathlib import Path
import os,subprocess,json,hashlib
root=Path(__file__).resolve().parents[5];v4=root/'hardware/glove-v4';out=Path('/tmp/thermal-readout-proposal');out.mkdir(exist_ok=True)
model=root/'hardware/glove-v3/simulation/power_validation/models/MCP6001-original.lib'
ng=Path('/tmp/glove-eda-runtime/usr/bin/ngspice');scripts=out/'scripts';scripts.mkdir(exist_ok=True)
(scripts/'spinit').write_text('\n'.join('codemodel '+str(x) for x in sorted((ng.parent.parent/'lib/x86_64-linux-gnu/ngspice').glob('*.cm')))+'\nset ngbehavior=ps\n')
rows=[]
for name,vdd,vexc in [('nominal',3.3,2.5),('low_rail',3.111665494505495,2.55)]:
 w=out/name;w.mkdir(exist_ok=True)
 deck=f'''* Proposal only; original MCP6001/2/4 model; room-temperature original model (ngspice27C).
.include "{model}"
VDD vdd 0 {vdd}
VIN inp 0 {vexc}
XBUF inp fb vdd 0 raw MCP6001
RISO raw out 47
RF out fb 10k
CF raw fb 100n
CP out 0 1u
RL out 0 1Meg
ILOAD out 0 PULSE(0 5.81m 5m 1u 1u 20m 50m)
.options method=gear reltol=1e-5 abstol=1e-12 gmin=1e-13 maxord=2
.control
set wr_singlescale
set wr_vecnames
tran 5u 35m 0 2u
let actual_end=time[length(time)-1]
print actual_end
wrdata waveform.dat v(out) v(raw)
quit
.endc
.end
'''
 (w/'circuit.cir').write_text(deck)
 env={**os.environ,'SPICE_SCRIPTS':str(scripts),'LD_LIBRARY_PATH':'/tmp/glove-eda-runtime/usr/lib/x86_64-linux-gnu'}
 with (w/'run.log').open('w') as f:r=subprocess.run([str(ng),'-b',str(w/'circuit.cir')],cwd=w,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=45)
 log=(w/'run.log').read_text();data=[[float(x) for x in l.split()] for l in (w/'waveform.dat').read_text().splitlines()[1:]] if (w/'waveform.dat').exists() else []
 complete=r.returncode==0 and data and data[-1][0]>=.034999 and not any(x in log.lower() for x in ['timestep too small','simulation(s) aborted'])
 row={'name':name,'complete':bool(complete),'supply_V':vdd,'setpoint_V':vexc,'load_A':.00581,'end_s':data[-1][0] if data else None,'deck_sha256':hashlib.sha256(deck.encode()).hexdigest(),'log_sha256':hashlib.sha256(log.encode()).hexdigest()}
 if complete:
  win=[r for r in data if .005<=r[0]<.025];late=[r for r in win if r[0]>.024];final=sum(r[1] for r in late)/len(late)
  bad=[r for r in win if abs(r[1]-final)>.001*vexc]
  row.update({'output_min_V':min(r[1] for r in win),'settled_V':final,'raw_output_max_V':max(r[2] for r in late),'settling_0p1percent_s':bad[-1][0]-.005 if bad else 0})
 rows.append(row)
(out/'vexc-results.json').write_text(json.dumps({'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'scope':'room-temperature original model (ngspice27C) original vendor model, no high-temperature or part-guaranteed output-current proof','cases':rows},indent=2)+'\n');print(json.dumps(rows,indent=2))
