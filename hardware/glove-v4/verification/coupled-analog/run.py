#!/usr/bin/env python3
"""Canonical 20-channel charge/filter network with real shared bias buffers.

Original manufacturer amplifier/diode equations. Supply/reference are explicitly
ideal boundary conditions; pressure contacts are resistance stimuli, not a
material/force model. No board parasitic extraction or converter certification.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, time
import numpy as np
P=Path(__file__).resolve().parent
V4=P.parents[1]
V3=V4.parent/'glove-v3'
SITES='I1 I2 I3 M1 M2 M3 R1 R2 R3 L1 L2 L3 T1 T2 P1 P2 P3 P4 H1 H2'.split()
MODELS={'mcp':V3/'simulation/vendor/MCP6001-rev-C.lib', 'diode':V3/'simulation/vendor/BAV199.lib', 'opa':V3/'simulation/vendor/OPAx320-prefixed.lib'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

SOLVER_PROFILES={
    'strict': 'method=gear reltol=1e-4 abstol=1e-12 gmin=1e-13 maxord=2 itl1=500 itl4=100',
    'conditioned': 'method=gear reltol=1e-3 abstol=1e-9 gmin=1e-9 maxord=2 itl1=1000 itl4=500',
    'conditioned_lower_gmin': 'method=gear reltol=1e-3 abstol=1e-9 gmin=1e-10 maxord=2 itl1=1000 itl4=500',
    'conditioned_lower_abstol': 'method=gear reltol=1e-3 abstol=1e-12 gmin=1e-9 maxord=2 itl1=1000 itl4=500',
}

def generate(case, rail=3.3, extra_c=1e-9, solver_profile='strict'):
    source=V4/'electrical/components.json'
    components=json.loads(source.read_text())['components']; cs={c['ref']:c for c in components}
    selected=[]
    def node(s):return '0' if s=='GND' else s.replace('+','_p').replace('-','_n')
    lines=['* V4 exact canonical shared tactile network, typical vendor macros',
           f'VRAIL 3V3_A 0 {rail}', 'VREFERENCE VREF3V0 0 3',
           '* Ideal settled rail/reference: excludes LDO/reference dynamics.',
           '.ic v(VMID1V25)=1.25 v(VMID_DIV)=1.25 v(VMID_BUF_IN)=1.25 v(VEXC2V5)=2.5 v(VEXC_FB)=2.5 v(VEXC_DRV)=2.5 v(VEXC_DIV)=2.5 v(ADC_NEG_OUT)=1.25 v(ADC_AIN_n)=1.25',
           f'CEXTRA VMID1V25 0 {extra_c}',
           '* All20 pressure contacts move from1Gohm to1ohm at95ms, release115ms.',
           'VCONTACT contact_conductance 0 PWL(0 1n 95m 1n 95.001m 1 115m 1 115.001m 1n)']
    def passive(ref):
        c=cs[ref]; assert c['ref'][0] in 'RC' and set(c['pins'])=={'1','2'},ref
        lines.append(f"{ref} {node(c['pins']['1'])} {node(c['pins']['2'])} {c['value']}");selected.append(ref)
    for ref in ['R_VEXC_H','R_VEXC_L','R_VEXC_ISO','R_VEXC_FB','C_VEXC_FB','C_VEXC','R_VMID_H','R_VMID_L','C_VMID','R_VMID_IN','R_ADC_NEG_ISO','C_ADC_NEG_BUCKET']:
        passive(ref)
    for c in components:
        if c.get('mpn')=='MCP6004T-I/ST':
            selected.append(c['ref']);p=c['pins']
            for k,(pp,nn,oo) in enumerate([(3,2,1),(5,6,7),(10,9,8),(12,13,14)]):
                lines.append(f"X{c['ref']}_{k} {node(p[str(pp)])} {node(p[str(nn)])} {node(p['4'])} {node(p['11'])} {node(p[str(oo)])} MCP6001")
    c=cs['U_VMID'];selected.append(c['ref']);p=c['pins']
    assert c['mpn']=='MCP6002T-I/SN'
    for k,(pp,nn,oo) in enumerate([(3,2,1),(5,6,7)]):
        lines.append(f"XBIAS{k} {node(p[str(pp)])} {node(p[str(nn)])} {node(p['8'])} {node(p['4'])} {node(p[str(oo)])} MCP6001")
    c=cs['U_ADC_NEG'];selected.append(c['ref']);p=c['pins'];assert c['mpn']=='OPA320AIDBVR'
    lines.append(f"XNEG {node(p['3'])} {node(p['4'])} {node(p['5'])} {node(p['2'])} {node(p['1'])} opa320_OPAx320")
    for site in SITES:
        for prefix in ['RFB','CFB','RIN','RS1A','RS1B','CS1FB','CS1G','RS2A','RS2B','CS2FB','CS2G','RPD']:
            passive(prefix+'_'+site)
        c=cs['D_CLAMP_'+site]; selected.append(c['ref'])
        assert c['mpn']=='BAV199,215' and c['pins']=={'1':'VMID1V25','2':'VMID1V25','3':'CHG_IN_'+site}
        lines.extend([f'DCLP_{site} CHG_IN_{site} VMID1V25 BAV199',f'DCLN_{site} VMID1V25 CHG_IN_{site} BAV199',
                      f'CPV_{site} PVDF_{site} 0 531p',f'CCABLE_{site} PVDF_{site} 0 150p',
                      f'CLOAD_{site} S2_OUT_{site} 0 5p',
                      f'BPC_{site} VEXC2V5 PRESS_{site} I=V(VEXC2V5,PRESS_{site})*V(contact_conductance)'])
        q=-250 if case=='single_negative' else 250
        if case=='all_positive' or site=='I1':
            lines.append(f'IPULSE_{site} 0 PVDF_{site} PULSE(0 {q}u 80m 100n 100n 900n 1s)')
        for n in ['PVDF','CHG_IN','CHG_OUT','S1_A','S1_B','S1_OUT','S2_A','S2_B','S2_OUT']:
            lines.append(f'.ic v({n}_{site})=1.25')
    selected=sorted(selected);assert len(selected)==289,(len(selected),selected)
    for path in MODELS.values():lines.append(f'.include "{path}"')
    traces=['VEXC2V5','VMID1V25','ADC_AIN_n','S2_OUT_I1','S2_OUT_I2','S2_OUT_H2','CHG_OUT_I1','PRESS_I1','VEXC_DRV']
    lines.extend(['.options '+SOLVER_PROFILES[solver_profile], '.temp 27',
                  '.control','option klu','set wr_singlescale','set wr_vecnames','set numdgt=12',
                  'save '+' '.join('v('+n+')' for n in traces),
                  'tran 2u 135m 0 2u','let actual_simulation_end=time[length(time)-1]',
                  'print actual_simulation_end','wrdata waveform.dat '+' '.join('v('+n+')' for n in traces),
                  'quit','.endc','.end'])
    # Nodeset guides the operating point; it does not force a capacitor voltage.
    lines=[line.replace('.ic ','.nodeset ',1) if line.startswith('.ic ') else line for line in lines]
    # Manufacturer noise diodes carry423uA withIs1fA. A~0.69V DC guess
    # aids sparse-matrix initialization without changing an equation or element.
    instances=[line.split()[0] for line in lines if line.startswith('X') and line.endswith(' MCP6001')]
    for instance in instances:
        lines.insert(lines.index('.control'),f'.nodeset v({instance}.20)=.69 v({instance}.21)=-.69')
    assert sum(line.startswith('X') for line in lines)==63
    return '\n'.join(lines)+'\n',{'case':case,'solver_profile':solver_profile,'solver_options':SOLVER_PROFILES[solver_profile],'canonical_sha256':sha(source),'component_refs':selected,'component_count':len(selected),'active_amplifier_sections':63,'supply_V':rail,'ideal_reference_V':3,'direct_vmid_parasitic_F':extra_c,'model_sha256':{k:sha(v) for k,v in MODELS.items()},'trace_nodes':traces}

def analyze_waveform(f, meta, case, display):
    """Strict native-data checks and shared metrics; completion is separate from qualification."""
    x=np.loadtxt(f,skiprows=1);t=x[:,0];assert np.isfinite(x).all() and x.shape[1]==10 and np.all(np.diff(t)>0) and abs(t[-1]-.135)<1e-9
    baseline=x[(t>.075)&(t<.079),1:].mean(axis=0);v=x[:,1:];diff=v[:,3:6]-v[:,2,None];base_diff=baseline[3:6]-baseline[2]
    pulse=(t>=.080)&(t<.094);pressure=(t>=.095)&(t<.115);recovery=t>.134
    peaks=np.max(abs(diff[pulse]-base_diff),axis=0)
    meta.update(samples=len(x),waveform_sha256=sha(f),baseline_V=dict(zip(meta['trace_nodes'],baseline.tolist())),pulse_differential_peak_V=dict(zip(['I1','I2','H2'],peaks.tolist())),quiet_to_active_peak_ratio=float(peaks[1]/peaks[0]) if case!='all_positive' and peaks[0] else None,pressure_step_vexc_min_V=float(v[pressure,0].min()),pressure_step_idle_differential_max_V=float(np.max(abs(diff[pressure,1]-base_diff[1]))),pressure_step_vexc_final_V=float(np.mean(v[(t>.114)&(t<.115),0])),recovery_differential_residual_V=(diff[recovery].mean(0)-base_diff).tolist(),post_warmup_min_V=v[t>.079].min(0).tolist(),post_warmup_max_V=v[t>.079].max(0).tolist())
    # Retain a bounded display trace as well as a hash of the full native output.
    np.savetxt(display,x[::max(1,len(x)//4000)],delimiter=',',header='time_s,'+','.join(meta['trace_nodes']),comments='')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['single_positive','single_negative','all_positive'],default='single_positive');ap.add_argument('--work',type=Path,required=True);ap.add_argument('--timeout',type=float,default=300);ap.add_argument('--ngspice',default='/tmp/glove-eda-runtime/usr/bin/ngspice');ap.add_argument('--solver-profile',choices=SOLVER_PROFILES,default='strict');a=ap.parse_args()
    d,meta=generate(a.case,solver_profile=a.solver_profile);w=a.work/a.case;w.mkdir(parents=True,exist_ok=True);deck=w/'circuit.cir';deck.write_text(d)
    scripts=w/'scripts';scripts.mkdir(exist_ok=True);models=Path(a.ngspice).parent.parent/'lib/x86_64-linux-gnu/ngspice'
    (scripts/'spinit').write_text('\n'.join('codemodel '+str(x) for x in sorted(models.glob('*.cm')))+'\nset ngbehavior=ps\n')
    env={**os.environ,'SPICE_SCRIPTS':str(scripts),'LD_LIBRARY_PATH':'/tmp/glove-eda-runtime/usr/lib/x86_64-linux-gnu'}
    log=w/'run.log';started=time.monotonic()
    with log.open('w') as out:
        try:r=subprocess.run([a.ngspice,'-b',str(deck)],cwd=w,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=a.timeout);rc=r.returncode
        except subprocess.TimeoutExpired:rc=124
    s=log.read_text();errors=[x for x in s.splitlines() if re.search(r'aborted|timestep too small|error:|fatal|singular matrix|no convergence',x,re.I)]
    ends=re.findall(r'actual_simulation_end\s*=\s*([-+0-9.eE]+)',s);end=float(ends[-1]) if ends else None
    meta.update(seconds=round(time.monotonic()-started,3),returncode=rc,native_end_s=end,complete=rc==0 and not errors and end is not None and abs(end-.135)<1e-9 and bool(re.search(r'ngspice-\S+ done',s)),errors=errors[-8:],deck_sha256=sha(deck),log_sha256=sha(log))
    if meta['complete']:
        analyze_waveform(w/'waveform.dat',meta,a.case,w/'display.csv')
    meta['numerical_qualification']='unresolved: a completed diagnostic alone is not tolerance-converged evidence'
    meta['limits']=['Electrical stimuli only; PVDF and Velostat force/texture behavior require physical characterization.','All20 active charge/filter chains and actual shared dual-loop excitation/midpoint plus ADC negative driver are connected.','Ideal3.3V analog rail and ideal3.0V reference omit supply/reference startup, dropout, noise and regulator interaction.','Temperature is27C solver setting; original typical macro models are not a process/temperature yield guarantee.','Mux/positive ADC driver, SAR sampling and PCB/harness parasitic coupling remain separate coverage.','1Gohm-to1ohm pressure contact transition is a deliberate aggregate electronics load bound, not a measured material response.','Macro-model noise and package thermal coupling are not included.']
    (w/'result.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({k:v for k,v in meta.items() if k not in ['component_refs','limits','baseline_V']},indent=2))
if __name__=='__main__':main()
