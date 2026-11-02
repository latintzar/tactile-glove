#!/usr/bin/env python3
"""Independent electrical, protocol and mechanical checks from ST DS13012."""
from pathlib import Path
import json, re, math, hashlib
P=Path(__file__).resolve().parent
d=json.loads((P/'imu-interface.json').read_text()); parts={p['ref']:p for p in d['parts']};checks=[]
def check(name,actual,expected):
 ok=actual==expected;checks.append(dict(name=name,pass_=ok,actual=actual,expected=expected))
 if not ok:raise AssertionError(checks[-1])
for suffix,addr in [('CUFF',106),('HAND',107)]:
 p=parts['U_IMU_'+suffix];n=p['pins'];check(suffix+' exact MPN',p['mpn'],'ISM330DHCXTR')
 check(suffix+' complete physical pin numbering',sorted(map(int,n)),list(range(1,15)))
 check(suffix+' mode1 CS',n['12'],'3V3_SYS');check(suffix+' address strap',n['1'],'GND' if addr==106 else '3V3_SYS')
 check(suffix+' supplies',[n['5'],n['8']],['3V3_SYS']*2)
 check(suffix+' grounds',[n[x] for x in ['2','3','6','7']],['GND']*4)
 check(suffix+' unused auxiliary ports',[n['10'],n['11']],['NC']*2)
 check(suffix+' local decouplers',[parts['C_IMU_'+suffix+'_'+s]['mpn'] for s in ['VDD','IO']],['GRM188R71C104KA01D']*2)
for j in ['J_IMU_CUFF','J_IMU_HAND']:
 check(j+' keyed pin order',parts[j]['pins'],{'1':'GND','2':'3V3_SYS','3':'I2C_SDA','4':'I2C_SCL'})
check('distinct device addresses',[x['address'] for x in d['devices']],[106,107])
check('no hand bus pullups',any(p['ref'].endswith('PULLUP') for p in d['parts']),False)
a=d['acquisition'];check('FS4 acceleration scaling',a['accelerometer_mg_per_lsb'],0.122);check('FS1000 gyro scaling',a['gyroscope_mdps_per_lsb'],35)
check('uncompressed FIFO record capacity',a['fifo_capacity_records'],512)
check('wire byte capacity includes tags',a['fifo_capacity_wire_bytes'],512*7)
r=2200*1.01;c=d['bus_budget']['capacitance_budget_pf']*1e-12;tr=.8473*r*c
check('400kHz rise time below300ns',tr<300e-9,True)
records_per_second=833*(2+1/8);payload_bytes_s=2*records_per_second*7
#10ms burst cycles, twoIMUs: status3+2 bytes, anchor3+4 bytes, FIFO3+ceil(payload/100) bytes.
#Start/stop timing overhead conservatively adds24 clock equivalents perdevice percycle.
clock_equiv=9*(payload_bytes_s+2*100*(5+7+3))+2*100*24
occupancy=clock_equiv/400000
check('FIFO polling1/10 of fill time',a['poll_interval_target_ms']/1000 < .1*512/records_per_second,True)
check('I2C occupancy below75percent',occupancy<.75,True)
#Exact KiCad library has manufacturer terminal centres and14unique lands.
f=P/'footprints/LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y.kicad_mod';t=f.read_text()
pads={int(n):(float(x),float(y)) for n,x,y in re.findall(r'\(pad (\d+) smd \w+ \(at ([-\d.]+) ([-\d.]+)\)',t)}
check('footprint14pins',sorted(pads),list(range(1,15)))
check('pin1 correct quadrant',pads[1][0]<0 and pads[1][1]<0,True)
check('left pins0.5mm pitch',[round(pads[i+1][1]-pads[i][1],3) for i in [1,2,3]],[.5]*3)
check('top pins0.5mm pitch',[round(pads[i][0]-pads[i+1][0],3) for i in [12,13]],[.5]*2)
result={'checks':checks,'passed':len(checks),'failed':0,'computed':{'worst_pullup_rise_ns':tr*1e9,'two_imu_payload_bytes_s':payload_bytes_s,'i2c_occupancy_fraction':occupancy,'fifo_fill_time_s_each':512/records_per_second,'minimum_accel_quantization_m_s2':.122e-3*9.80665},'source_sha256':hashlib.sha256((P/'imu-interface.json').read_bytes()).hexdigest(),'scope':'Checks pin mappings, bus arithmetic and footprint lands. Capacitance and timing allocations become final-layout verification constraints; these checks do not measure position accuracy.'}
(P/'imu-interface-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':len(checks),'computed':result['computed']}))
