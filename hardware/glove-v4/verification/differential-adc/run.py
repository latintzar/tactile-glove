#!/usr/bin/env python3
"""Actual two OPA320 paths + OPA4323, mux/SAR explicit RC equivalents.
Native endpoint, diagnostics, physical input bounds and firmware settling windows
are checked. This does not model the switched SAR converter or board parasitics.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess
import numpy as np
P=Path(__file__).resolve().parent; V4=P.parents[1]; ROOT=V4.parent.parent
VENDOR=V4.parent/'glove-v3/simulation/vendor'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--bias-ramp',action='store_true');a=ap.parse_args();a.work.mkdir(parents=True,exist_ok=True)
 c={x['ref']:x for x in json.loads((V4/'electrical/components.json').read_text())['components']}
 for ref,val in [('R_ADC_ISO','22'),('R_ADC_NEG_ISO','22'),('C_ADC_BUCKET','1n'),('C_ADC_NEG_BUCKET','1n')]:assert c[ref]['value']==val
 assert c['R_ADC_ISO']['pins']=={'1':'ADC_DRIVER_OUT','2':'ADC_AIN+'}
 assert c['R_ADC_NEG_ISO']['pins']=={'1':'ADC_NEG_OUT','2':'ADC_AIN-'}
 assert c['U_ADC_NEG']['pins']=={'1':'ADC_NEG_OUT','2':'GND','3':'VMID1V25','4':'ADC_NEG_OUT','5':'3V3_A'}
 for ref in ['U_ADC_DRV','U_ADC_NEG']:assert c[ref]['mpn']=='OPA320AIDBVR'
 assert c['U_BANK1']['mpn']=='OPA4323IPWR' and c['U_ADC']['mpn']=='MCP33131D-10-I/MS'
 contract=json.loads((ROOT/'firmware/tactile_v4/firmware-contract.json').read_text());timing=contract['tactile']
 assert timing['dynamic_settle_us']==6 and timing['pressure_settle_us']==24
 results=[];ng='/tmp/glove-eda-runtime/usr/bin/ngspice';scripts=a.work/'scripts';scripts.mkdir(exist_ok=True)
 cm=Path(ng).parent.parent/'lib/x86_64-linux-gnu/ngspice'
 (scripts/'spinit').write_text('\n'.join('codemodel '+str(x) for x in sorted(cm.glob('*.cm')))+'\nset ngbehavior=ps\n')
 for name,rs,rm,cap,lo,hi,settle in [('dynamic-up',0,1000,1,.1,2.5,6),('dynamic-down',0,1000,1,2.5,.1,6),('pressure-up',10000,1000,2,0,2.5,24),('pressure-down',10000,1000,2,2.5,0,24),('dynamic-resistance-stress',0,2000,2,.1,2.5,6)]:
  settle=timing['pressure_settle_us'] if name.startswith('pressure') else timing['dynamic_settle_us']
  w=a.work/name;w.mkdir(exist_ok=True)
  bias_line='VBIAS vmid 0 PWL(0 .1 1u .1 2u 1.25)' if a.bias_ramp else 'VBIAS vmid 0 1.25'
  deck=f'''* V4 differential ADC analog input network; original TI amplifier models
.include "{VENDOR/'OPAx323-prefixed.lib'}"
.include "{VENDOR/'OPAx320-prefixed.lib'}"
VDD vdd 0 3.3
{bias_line}
VIN src 0 PULSE({lo} {hi} 10u 1n 1n 100u 200u)
RSRC src source {rs+.001}
RM1 source bankin {rm}
CM1 bankin 0 {80*cap}p
XBANK bankin bankout vdd 0 bankout opa323_OPAx323
RM2 bankout driverin {rm}
CM2 driverin 0 {40*cap}p
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
.options method=gear reltol=1e-5 abstol=1e-12 gmin=1e-12 itl1=500 itl4=100
.control
set wr_singlescale
set wr_vecnames
set numdgt=12
tran 1n 80u 0 1n
let actual_simulation_end=time[length(time)-1]
print actual_simulation_end
wrdata waveform.dat v(src) v(adcplus) v(adcminus) v(sampleplus) v(sampleminus)
quit
.endc
.end
'''
  d=w/'circuit.cir';d.write_text(deck);log=w/'run.log'
  env={**os.environ,'SPICE_SCRIPTS':str(scripts),'LD_LIBRARY_PATH':'/tmp/glove-eda-runtime/usr/lib/x86_64-linux-gnu'}
  with log.open('w') as f:
   try:r=subprocess.run([ng,'-b',str(d)],cwd=w,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90);rc=r.returncode
   except subprocess.TimeoutExpired:rc=124
  s=log.read_text();errors=[line for line in s.splitlines() if re.search(r'aborted|timestep too small|error:|singular matrix|no convergence',line,re.I)]
  ends=re.findall(r'actual_simulation_end\s*=\s*([-+0-9.eE]+)',s);end=float(ends[-1]) if ends else None
  row={'case':name,'complete':rc==0 and not errors and end is not None and abs(end-80e-6)<1e-12 and bool(re.search(r'ngspice-\S+ done',s)),'native_end_s':end,'returncode':rc,'errors':errors[-6:],'deck_sha256':sha(d),'log_sha256':sha(log),'source_R_ohm':rs,'mux_R_each_ohm_assumed':rm,'mux_C_multiplier':cap,'settling_window_us':settle}
  if row['complete']:
   f=w/'waveform.dat';x=np.loadtxt(f,skiprows=1);assert np.isfinite(x).all() and x.shape[1]==6 and np.all(np.diff(x[:,0])>0) and abs(x[-1,0]-80e-6)<1e-12
   t=x[:,0];diff=x[:,4]-x[:,5];ref=3.;half_lsb=ref/65536.;residual=np.interp((10+settle)*1e-6,t,diff)-diff[-1];after=t>=10e-6;bad=np.flatnonzero(after&(abs(diff-diff[-1])>half_lsb));cmv=(x[:,2]+x[:,3])/2
   row.update(samples=len(x),waveform_sha256=sha(f),input_pin_min_V=float(x[:,2:4].min()),input_pin_max_V=float(x[:,2:4].max()),common_mode_min_V=float(cmv.min()),common_mode_max_V=float(cmv.max()),differential_final_V=float(diff[-1]),dc_error_V=float(diff[-1]-(hi-1.25)),sample_residual_V=float(residual),residual_at_previous_12us_V=float(np.interp(22e-6,t,diff)-diff[-1]),half_lsb_V=half_lsb,last_outside_half_lsb_us=float((t[bad[-1]]-10e-6)*1e6) if len(bad) else 0,sample_within_half_lsb=bool(abs(residual)<=half_lsb),within_input_absolute_limits=bool(x[:,2:4].min()>-.1 and x[:,2:4].max()<3.1),within_nominal_input_range=bool(x[:,2:4].min()>=0 and x[:,2:4].max()<=3))
   np.savetxt(w/'display.csv',x[::20],delimiter=',',header='time_s,source_V,AINplus_V,AINminus_V,sampleplus_V,sampleminus_V',comments='')
  (w/'result.json').write_text(json.dumps(row,indent=2)+'\n');results.append(row);print(name,row,flush=True)
 out={'bias_ramp_preconditioning':a.bias_ramp,'canonical_sha256':sha(V4/'electrical/components.json'),'timing_used':{'dynamic_us':timing['dynamic_settle_us'],'pressure_us':timing['pressure_settle_us']},'firmware_contract_sha256':sha(ROOT/'firmware/tactile_v4/firmware-contract.json'),'models':{f:sha(VENDOR/f) for f in ['OPAx323-prefixed.lib','OPAx320-prefixed.lib']},'cases':results,'limits':['Typical vendor amplifier models only; no process/temperature guarantee.','ADC load is a continuous31pF+200ohm equivalent on each input, not a switched SAR model.','Mux resistance/capacitance are explicit engineering stress assumptions, not guaranteed3.3V CD74HC limits.','Ideal3.3V supply/1.25V bias omit shared reference and power interaction.','Settling residual is relative to final modeled value; separately reported DC error is not hidden by that metric.','A complete simulator run is distinct from a passed performance criterion.']}
 (a.work/'results.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
