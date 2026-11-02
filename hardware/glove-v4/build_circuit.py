#!/usr/bin/env python3
"""Merge the reviewed analogue core and V4 interfaces into one circuit source."""
from pathlib import Path
from collections import Counter, defaultdict
import copy, hashlib, json, re
P=Path(__file__).resolve().parent
OUT=P/'electrical'; OUT.mkdir(exist_ok=True)
OLD=P.parent/'glove-v3'/'electrical'
REMOVED={'J_XIAO','J_BAT','J_IMU','U_IOX','SW1','U_LOAD','R_ANALOG_EN',
         'R_WAKE','R_BTN0','R_I2C_SDA','R_I2C_SCL','C_LOAD_IN','C_LOAD_OUT'}
NETS={'3V3':'3V3_SYS','3V3A':'3V3_A','ADC_MISO':'ADC_SDO',
      'MUX_SRCLK':'MUX_SHIFT_CLK','MUX_SER':'MUX_DATA','MUX_RCLK':'MUX_LATCH'}
sources={}
def read(path):
    raw=path.read_bytes();sources[str(path.relative_to(P.parent.parent))]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)
old=read(OLD/'components.json')['components']
assert REMOVED <= {p['ref'] for p in old}, REMOVED-{p['ref'] for p in old}
parts=[]
for original in old:
    if original['ref'] in REMOVED:continue
    p=copy.deepcopy(original);p['pins']={n:NETS.get(net,net) for n,net in p['pins'].items()}
    p['subsystem']='tactile';p.pop('status',None)
    # Keep descriptions aligned with the canonical MPN/value. Historical V3
    # labels say 100M/100pF although these parts are 22 MOhm/470 pF.
    if p['ref'].startswith('RFB_') and p.get('value') == '22Meg':
        p['function']='22M charge feedback'
    if p['ref'].startswith('CFB_') and p.get('value') == '470p':
        p['function']='470pF C0G charge feedback'
    if p['ref']=='U_REF':p['pins']['1']='VREF_SUPPLY'
    if p['ref']=='U_ADC':p['pins']['9']=p['pins']['10']='3V3_SYS'
    if p['ref']=='C_ADC_DVIO':p['pins']['1']='3V3_SYS'
    if p['ref']=='D_LDO_REV':p['footprint']='GlovePower:Nexperia_CFP3_SOD123W'
    parts.append(p)
for path,subsystem in [(P/'power/power-circuit.json','power'),
    (P/'interfaces/camera-interface.json','camera'),(P/'interfaces/imu-interface.json','imu'),
    (P/'interfaces/sd-interface.json','sd')]:
    for original in read(path)['parts']:
        if subsystem=='imu' and original['assembly']!='cuff':continue
        p=copy.deepcopy(original);p['subsystem']=subsystem;parts.append(p)
duplicates=[ref for ref,n in Counter(p['ref'] for p in parts).items() if n>1]
assert not duplicates,duplicates
refmap=read(OLD/'reference-map.json');next_ref=defaultdict(int)
for ref in refmap.values():
    m=re.fullmatch(r'([A-Z]+)(\d+)',ref)
    if m:next_ref[m[1]]=max(next_ref[m[1]],int(m[2]))
used={p['ref']:refmap[p['ref']] for p in parts if p['ref'] in refmap and p['subsystem']=='tactile'}
for p in parts:
    if p['ref'] not in used:
        prefix=p['ref'].split('_')[0]
        assert prefix in ['U','R','C','D','Q','L','J','SW','F','TP'],prefix
        next_ref[prefix]+=1;used[p['ref']]=prefix+str(next_ref[prefix])
    p['designator']=used[p['ref']]
assert len(set(used.values()))==len(parts)
nets=defaultdict(list)
for p in parts:
    for pin,net in p['pins'].items():
        if net!='NC':nets[net].append([p['ref'],pin])
assert not set(NETS)&set(nets)
data=dict(schema=1,revision='V4 continuous-camera tactile cuff',components=parts,
    source_sha256=sources,subsystems=dict(Counter(p['subsystem'] for p in parts)),
    removed_v3_parts=sorted(REMOVED),
    scope='Main cuff; hand IMU tile and soft sensor harness are separate assemblies.',
    status='Integrated circuit; manufacturing export follows schematic/board reconciliation.')
for filename,obj in [('components.json',data),('reference-map.json',used),('net-endpoints.json',dict(sorted(nets.items())))]:
    (OUT/filename).write_text(json.dumps(obj,indent=2)+'\n')
print(len(parts),'components;',len(nets),'nets;',sum(map(len,nets.values())),'connected pins;',data['subsystems'])
