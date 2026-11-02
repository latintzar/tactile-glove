#!/usr/bin/env python3
"""Original MCP6002+OPA4323+OPA320 models; explicit selected-mux RC stress."""
from pathlib import Path
import argparse,gzip,hashlib,json,os,re,subprocess
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];V4=ROOT/'hardware/glove-v4'
MODEL=ROOT/'hardware/glove-v3/simulation/power_validation/models/MCP6001-original.lib'
VENDOR=ROOT/'hardware/glove-v3/simulation/vendor'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,default=Path('/tmp/thermal-buffer-proposal'));a=ap.parse_args();a.work.mkdir(exist_ok=True)
 ng=Path('/tmp/glove-eda-runtime/usr/bin/ngspice');scripts=a.work/'scripts';scripts.mkdir(exist_ok=True)
 (scripts/'spinit').write_text('\n'.join('codemodel '+str(x) for x in sorted((ng.parent.parent/'lib/x86_64-linux-gnu/ngspice').glob('*.cm')))+'\nset ngbehavior=ps\n')
 rows=[]
 for name,old,rntc,leak in [('select40_from_low',.025,5827,8e-6),('select40_from_high',2.55,5827,-8e-6),('open',.025,1e12,8e-6),('short',2.55,.001,-8e-6)]:
  w=a.work/name;w.mkdir(exist_ok=True)
  deck=f'''* Unapplied buffered NTC proposal. Typical25C; supply lower-bound stress.
.include "{MODEL}"
.include "{VENDOR/'OPAx323-prefixed.lib'}"
.include "{VENDOR/'OPAx320-prefixed.lib'}"
VDD vdd 0 3.111665494505495
VEXC vex 0 2.55
VBIAS vmid 0 1.275
RPU vex ntc 10k
RNTC ntc 0 {rntc}
CFILT ntc 0 100n
XBUF ntc raw vdd 0 raw MCP6001
RBUF raw buffered 100
VOLD old 0 {old}
VSEL select 0 PULSE(0 1 10u 1n 1n 1m 2m)
BSELECT selected 0 V=V(old)*(1-V(select))+V(buffered)*V(select)
* The controlled selector duplicates the buffered voltage. This resistor+cap
* path also loads the real buffer for conservative continuous mux loading.
RLOAD buffered bufload 2000
CLOAD bufload 0 160p
IBUFLOAD bufload 0 DC {leak}
RM1 selected bankin 2000
CM1 bankin 0 160p
ILEAK bankin 0 DC {leak}
XBANK bankin bankout vdd 0 bankout opa323_OPAx323
RM2 bankout driverin 2000
CM2 driverin 0 80p
XDRV driverin driverout vdd 0 driverout opa320_OPAx320
XNEG vmid negout vdd 0 negout opa320_OPAx320
RISO driverout adcplus 22
CBUCKET adcplus 0 1n
RNEGIS negout adcminus 22
CNEGBUCKET adcminus 0 1n
RSAMPLEP adcplus sampleplus 200
CSAMPLEP sampleplus 0 31p
RSAMPLEN adcminus sampleminus 200
CSAMPLEN sampleminus 0 31p
.temp 25
.options method=trap reltol=1e-4 abstol=1e-10 gmin=1e-12 itl1=500 itl4=100
.control
set wr_singlescale
set wr_vecnames
set numdgt=12
tran 2n 80u 0 2n
let actual_simulation_end=time[length(time)-1]
print actual_simulation_end
wrdata waveform.dat v(ntc) v(raw) v(buffered) v(adcplus) v(adcminus) v(sampleplus) v(sampleminus)
quit
.endc
.end
'''
  (w/'circuit.cir').write_text(deck)
  env={**os.environ,'SPICE_SCRIPTS':str(scripts),'LD_LIBRARY_PATH':'/tmp/glove-eda-runtime/usr/lib/x86_64-linux-gnu'}
  with (w/'run.log').open('w') as f:
   try:rc=subprocess.run([str(ng),'-b',str(w/'circuit.cir')],cwd=w,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60).returncode
   except subprocess.TimeoutExpired:rc=124
  log=(w/'run.log').read_text();errors=[l for l in log.splitlines() if re.search('timestep too small|aborted|singular matrix|no convergence|error:',l,re.I)]
  ends=re.findall(r'actual_simulation_end\s*=\s*([-+0-9.eE]+)',log);end=float(ends[-1]) if ends else None
  complete=rc==0 and not errors and end is not None and abs(end-80e-6)<1e-12 and bool(re.search(r'ngspice-\S+ done',log))
  row={'case':name,'complete':complete,'native_end_s':end,'returncode':rc,'errors':errors,'mux_R_each_ohm_assumed':2000,'mux_C_pF_assumed':[160,80],'leakage_A_assumed':leak,'deck_sha256':sha(w/'circuit.cir'),'log_sha256':sha(w/'run.log')}
  if complete:
   x=np.loadtxt(w/'waveform.dat',skiprows=1);assert np.isfinite(x).all();t=x[:,0];diff=x[:,6]-x[:,7];final=diff[-1]
   residual=float(np.interp(34e-6,t,diff)-final);bad=np.flatnonzero((t>=10e-6)&(abs(diff-final)>3/65536))
   row.update({'samples':len(x),'input_node_V':float(x[-1,1]),'buffer_output_V':float(x[-1,2]),'ADC_positive_V':float(x[-1,4]),'ADC_negative_V':float(x[-1,5]),'differential_final_V':float(final),'sample_residual_24us_V':residual,'sample_within_half_LSB':abs(residual)<=3/65536,'last_outside_half_LSB_us':float((t[bad[-1]]-10e-6)*1e6) if len(bad) else 0,'DC_error_against_divider_V':float(x[-1,4]-x[-1,1]),'waveform_sha256':sha(w/'waveform.dat')})
   with gzip.open(w/'waveform.dat.gz','wb') as f:f.write((w/'waveform.dat').read_bytes())
  rows.append(row);print(row,flush=True)
 (a.work/'results.json').write_text(json.dumps({'scope':'Typical25C; original vendor models. Mux RC/current are declared stress values; SAR31pF+200ohm continuous equivalent. Selector uses buffered voltage with separate conservative continuous load, not transistor switch charge injection.','models':{str(f.relative_to(ROOT)):sha(f) for f in [MODEL,VENDOR/'OPAx323-prefixed.lib',VENDOR/'OPAx320-prefixed.lib']},'cases':rows},indent=2)+'\n')
if __name__=='__main__':main()
