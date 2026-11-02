"""Publish a verified routing checkpoint atomically, with honest readiness."""
from pathlib import Path
import pcbnew as k,json,hashlib,os,collections,datetime,sys
E=Path(sys.argv[2]);src=Path(sys.argv[1]);P=src.parent;b=k.LoadBoard(str(src));parts=json.loads((E/'components.json').read_text())['components'];fps={f.GetReference():f for f in b.GetFootprints()};errors=[]
for c in parts:
 f=fps[c['designator']]
 for p in f.Pads():
  n=p.GetNumber()
  if n not in c['pins']:continue
  want=c['pins'][n];want='' if want=='NC' else want
  if p.GetNetname()!=want:errors.append([c['designator'],n,want,p.GetNetname()])
assert not errors,errors
assert len(fps)==len(parts)
s=src.with_suffix('.drc.txt').read_text();counts=dict(collections.Counter(x.split(']')[0] for x in s.split('\n[')[1:]));physical=sum('Severity: error' in x for x in s.split('\n[')[1:] if not x.startswith('unconnected_items]'));assert physical==0
files={'glove-v4-routing-candidate.kicad_pcb':src.read_bytes(),'glove-v4-routing-candidate.kicad_pro':src.with_suffix('.kicad_pro').read_bytes(),'routing-candidate.drc.txt':s.replace(str(src),'glove-v4-routing-candidate.kicad_pcb').encode()}
for name in ['fanout_opens.py','island_endpoints.py','repair_islands.py','route_multi.py','island_multi.py','repair_multi.py','export_shove.py','publish_candidate.py']:files[name]=(P/name).read_bytes()
status=json.loads((E/'routing-progress.json').read_text());status.update(unconnected_items=counts.get('unconnected_items',0),physical_drc_errors=0,report_counts=counts,candidate_sha256=hashlib.sha256(files['glove-v4-routing-candidate.kicad_pcb']).hexdigest(),components_sha256=hashlib.sha256((E/'components.json').read_bytes()).hexdigest(),canonical_pad_net_mismatches=0,verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),current_process='Bounded signal-shove and whole-island repairs continue in /tmp/glove-v4-routing-cache',manufacturing_ready=False)
files['routing-progress.json']=(json.dumps(status,indent=2)+'\n').encode()
for name,data in files.items():
 dst=E/name;tmp=dst.with_name(dst.name+'.tmp');tmp.write_bytes(data);os.chown(tmp,1003,1003);os.replace(tmp,dst)
print(json.dumps(status,indent=2))
