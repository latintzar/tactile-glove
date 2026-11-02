raise SystemExit("Historical migration: already applied. Edit components.json and run generate_native.py; this migration must not run again.")
"""Correct the physical circuit graph; retained to audit the superseded candidate."""
from pathlib import Path
import json,csv
P=Path(__file__).parent
raw=json.loads((P/'components.json').read_text()); parts=raw['components']; C={p['ref']:p for p in parts}
ids=[f'{f}{i}' for f,n in [('I',3),('M',3),('R',3),('L',3),('T',2),('P',4),('H',2)] for i in range(1,n+1)]
# Unified names in each Sallen-Key section. Each amplifier is a follower.
for p in parts:
 p['pins']={k:v.replace('SK1_','S1_').replace('SK2_','S2_').replace('BAT-','GND') for k,v in p['pins'].items()}
units=[('1','2','3'),('7','6','5'),('8','9','10'),('14','13','12')]
for i,cell in enumerate(ids):
 for stage in [1,2]:
  j=i*2+stage-1; amp=C[f'U_FILT{j//4+1}']['pins']; o,m,n=units[j%4]
  amp[o]=amp[m]=f'S{stage}_OUT_{cell}';amp[n]=f'S{stage}_B_{cell}'
C['U_VMID']['pins']={'1':'VEXC2V5','2':'VEXC2V5','3':'VREF2V5','4':'GND','5':'VMID_DIV','6':'VMID1V25','7':'VMID1V25','8':'3V3'}
# Four independent ten-channel banks. Firmware: pressure banks0,1; vibration2,3.
chanpins=[9,8,7,6,5,4,3,2,23,22,21,20,19,18,17,16]
for bank in range(4):
 p=C[f'U_MUX{bank+1}']['pins'];p.update({'1':f'MUX{bank+1}_COM','10':'MUX_A0','11':'MUX_A1','14':'MUX_A2','13':'MUX_A3','12':'GND','15':'GND','24':'3V3'})
 for slot,pin in enumerate(chanpins):
  p[str(pin)]=('PRESS_' if bank<2 else 'S2_OUT_')+ids[(bank%2)*10+slot] if slot<10 else 'VMID1V25'
for bank in range(4):
 p=C[f'U_BANK{bank//2+1}']['pins'];o,m,n=units[bank%2];p[o]=p[m]=f'MUX{bank+1}_BUF';p[n]=f'MUX{bank+1}_COM'
for name in ['U_BANK1','U_BANK2']:
 for k in [2,3]:
  o,m,n=units[k];C[name]['pins'][o]=C[name]['pins'][m]=f'UNUSED_{name}_{k}';C[name]['pins'][n]='VMID1V25'
# Use A half of 4052; tie all unused B inputs to bias; B output unconnected.
C['U_MUX_FINAL']['pins']={'1':'VMID1V25','2':'VMID1V25','3':'NC','4':'VMID1V25','5':'VMID1V25','6':'GND','7':'GND','8':'GND','9':'MUX_BANK1','10':'MUX_BANK0','11':'MUX4_BUF','12':'MUX1_BUF','13':'ADC_MUX','14':'MUX2_BUF','15':'MUX3_BUF','16':'3V3'}
C['U_ADC_DRV']['pins']={'1':'ADC_DRIVER_OUT','2':'GND','3':'ADC_MUX','4':'ADC_DRIVER_OUT','5':'3V3'}
# PCF8574 SO16: A0/A1/A2, P0..P7, /INT,SCL,SDA.
C['U_IOX']['pins']={'1':'GND','2':'GND','3':'GND','4':'BTN0','5':'BTN1','6':'NC','7':'NC','8':'GND','9':'NC','10':'NC','11':'NC','12':'NC','13':'NC','14':'I2C_SCL','15':'I2C_SDA','16':'3V3'}
# Module connectors use standard STEMMA QT pinout; module is a separate BOM assembly.
for ref in ['J_IMU','J_OLED']:
 C[ref].update(mpn='SM04B-SRSS-TB(LF)(SN)',package='JST SH 1mm side entry 4',pins={'1':'GND','2':'3V3','3':'I2C_SDA','4':'I2C_SCL'})
parts=[p for p in parts if p['ref']!='J_USB'] # USB-C already inside XIAO module, not a duplicate purchased connector.
def add(ref,mpn,package,pins,function,value=None):
 p={'ref':ref,'qty':1,'mpn':mpn,'package':package,'pins':pins,'function':function,'status':'candidate; procurement and board validation pending'}
 if value:p['value']=value
 parts.append(p)
add('R_VMID_H','RC0603FR-0710KL','0603',{'1':'VREF2V5','2':'VMID_DIV'},'midpoint divider upper','10k')
add('R_VMID_L','RC0603FR-0710KL','0603',{'1':'VMID_DIV','2':'GND'},'midpoint divider lower','10k')
add('C_VMID','GRM188R61A105KA61D','0603',{'1':'VMID_DIV','2':'GND'},'midpoint divider bypass','1u')
add('R_ADC_ISO','RC0603FR-0722RL','0603',{'1':'ADC_DRIVER_OUT','2':'ADC_AIN+'},'ADC input driver isolation resistor candidate','22')
add('C_ADC_BUCKET','GRM1885C1H102JA01D','0603',{'1':'ADC_AIN+','2':'GND'},'ADC charge reservoir; settle and stability check required','1n')
for name in ['I2C_SDA','I2C_SCL']:
 add('R_'+name,'RC0603FR-074K7L','0603',{'1':'3V3','2':name},'I2C pull-up; module parallel pullups must be counted','4.7k')
for i in range(2):add('SW'+str(i+1),'PTS636 SK43 SMTR LFS','switch 6x3.5mm',{'1':f'BTN{i}','2':'GND'},'momentary push button')
for p in parts:
 ref=p['ref'];p['status']='topology corrected; physical CAD and supplier verification pending'
 if ref.startswith('RFB_'):p.update(value='100Meg',mpn='UNRESOLVED_100M_1percent',package='0805')
 if ref.startswith('CFB_'):p['value']='100p'
 if ref.startswith('RIN_'):p['value']='1k'
 if ref.startswith('RS1'):p['value']='14.7k'
 if ref.startswith('RS2'):p['value']='27.4k'
 if ref.startswith('CS1FB'):p['value']='12n'
 if ref.startswith('CS1G'):p['value']='10n'
 if ref.startswith('CS2FB'):p['value']='15n'
 if ref.startswith('CS2G'):p['value']='2.2n'
 if ref.startswith('RPD_'):p['value']='10k'
 if ref.startswith('CDEC_'):p['value']='100n'
 if ref in ['C_LDO_IN','C_LDO_OUT']:p['value']='1u'
raw.update(components=parts,status='Corrected topology candidate; manufacture gate open',scope='20 pressure +20 local vibration readout plus MCU/IMU/display interfaces')
(P/'components.json').write_text(json.dumps(raw,indent=2)+'\n')
with (P/'nets.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['net','ref','pin'])
 for p in parts:
  for pin,net in p['pins'].items():
   if net!='NC':w.writerow([net,p['ref'],pin])
print(len(parts),'components corrected')
