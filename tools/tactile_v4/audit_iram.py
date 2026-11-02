#!/usr/bin/env python3
"""Audit direct and literal-resolved calls in the exact target capture ISR."""
import argparse,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--elf',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
nm=subprocess.check_output(['xtensa-esp32s3-elf-nm','-S','-n','-C',str(a.elf)],text=True)
selected=[]
for line in nm.splitlines():
 if 'V4::Acquisition::capture<V4::Adc>' in line or ' tick(gptimer_t*' in line:
  fields=line.split(maxsplit=3);selected.append((int(fields[0],16),int(fields[1],16),fields[3]))
assert len(selected)==2
report=[];assembly=[]
def classification(address):
 if 0x40000000<=address<0x40080000:return 'ROM'
 if 0x40370000<=address<0x403E0000:return 'IRAM'
 raise AssertionError(f'ISR call targets non-IRAM/ROM address {address:#x}')
for address,size,name in selected:
 classification(address)
 text=subprocess.check_output(['xtensa-esp32s3-elf-objdump','-d','-C',f'--start-address={address}',f'--stop-address={address+size}',str(a.elf)],text=True);assembly.append(text);lines=text.splitlines();calls=[]
 assert '__atomic' not in text
 for i,line in enumerate(lines):
  direct=re.search(r'call(?:0|4|8|12)\s+([0-9a-f]+) <(.+)>',line)
  if direct:calls.append({'name':direct[2],'address':direct[1],'region':classification(int(direct[1],16))})
  elif re.search(r'callx(?:0|4|8|12)\s+a8',line):
   candidates=[re.search(r'l32r\s+a8,.*\(([0-9a-f]+) <(.+)>\)',old) for old in lines[max(0,i-8):i]];candidates=[x for x in candidates if x]
   assert candidates,f'unresolved indirect call: {line}'
   target=candidates[-1];calls.append({'name':target[2],'address':target[1],'region':classification(int(target[1],16))})
 report.append({'symbol':name,'address':hex(address),'bytes':size,'calls':calls})
(a.output/'capture-disassembly.txt').write_text('\n'.join(assembly))
(a.output/'iram-audit.json').write_text(json.dumps({'status':'pass','functions':report,'no_atomic_lock_helpers_in_capture_or_tick':True,'scope':'Call targets of capture and tick; selected GPTIMER implementation is enabled as IRAM-safe. This is not measured cycle timing.'},indent=2)+'\n')
print('capture/tick IRAM call audit passed')
