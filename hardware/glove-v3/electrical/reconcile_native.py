"""Compare independent KiCad XML nets, including every intentional NC, with manifest."""
from pathlib import Path
import json,xml.etree.ElementTree as ET,sys
P=Path(__file__).parent
parts=json.loads((P/'components.json').read_text())['components'];refs=json.loads((P/'reference-map.json').read_text())
expected={};nc=set()
for p in parts:
 for pin,net in p['pins'].items():
  pair=(refs[p['ref']],pin)
  if net=='NC':nc.add(pair)
  else:expected.setdefault(net,set()).add(pair)
actual={};seen_nc=set();errors=[]
for n in ET.parse(sys.argv[1]).findall('./nets/net'):
 pairs={(p.attrib['ref'],p.attrib['pin']) for p in n.findall('node')}
 if pairs<=nc and len(pairs)==1:seen_nc|=pairs
 else:actual[n.attrib['name']]=pairs
for net in expected.keys()|actual.keys():
 if expected.get(net)!=actual.get(net):errors.append({'net':net,'expected':sorted(expected.get(net,set())),'actual':sorted(actual.get(net,set()))})
if nc!=seen_nc:errors.append({'missing_nc':sorted(nc-seen_nc)})
r={'status':'pass' if not errors else 'fail','components':len(parts),'nets':len(expected),'connected_pins':sum(map(len,expected.values())),'intentional_nc_pins':len(nc),'mismatches':errors,'method':'Independent KiCad XML vs canonical numbered physical pins; intentional NC endpoints checked separately.'}
(P/'native-net-reconciliation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));sys.exit(bool(errors))
