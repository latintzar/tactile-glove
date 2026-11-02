"""Translate pinned library syntax, preserving electrical pad geometry exactly."""
from pathlib import Path
import re,json,hashlib,requests
P=Path(__file__).resolve().parent;F=P/'footprints';S=P/'footprint-originals';S.mkdir(exist_ok=True)
revision='f8440fa61a5690b48b325c891fdb99c0038a5a59'
def parse(s):
 tokens=re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+|[()]',s);stack=[];root=None
 for t in tokens:
  if t=='(':
   n=[]
   if stack:stack[-1].append(n)
   else:root=n
   stack.append(n)
  elif t==')':stack.pop()
  else:stack[-1].append(t)
 return root
def dump(x):return '('+' '.join(dump(v) if isinstance(v,list) else v for v in x)+')'
def child(n,k):return next((x for x in n if isinstance(x,list) and x[0]==k),None)
def pads(x):return [{k:child(n,k) for k in ['at','size','drill','layers','roundrect_rratio','rect_delta','options','primitives']}|{'number':n[1],'type':n[2],'shape':n[3]} for n in x if isinstance(n,list) and n[0]=='pad']
def clean(n):
 if not isinstance(n,list):return n
 if n and n[0] in ['uuid','generator_version','unlocked','tenting','remove_unused_layers','embedded_fonts','duplicate_pad_numbers_are_jumpers','placement']:return None
 if n and n[0]=='property':return None
 if n and n[0]=='fill' and len(n)==2 and n[1] in ['yes','no']:return ['fill','solid' if n[1]=='yes' else 'none']
 if n and n[0]=='version':return ['version','20221018']
 return [v for e in n if (v:=clean(e)) is not None]
parts=json.loads((P/'power-circuit.json').read_text())['parts'];sources=json.loads((P/'footprint-sources.json').read_text())
for fp in sorted({p['footprint'] for p in parts}):
 lib,name=fp.split(':');path=F/(name+'.kicad_mod');raw=path.read_bytes();x=parse(raw.decode())
 if (S/path.name).exists() or child(x,'generator_version') or (child(x,'version') and int(child(x,'version')[1])>20230101):
  original=S/path.name
  if not original.exists():
   url=f'https://gitlab.com/kicad/libraries/kicad-footprints/-/raw/{revision}/{lib}.pretty/{name}.kicad_mod';r=requests.get(url,timeout=20);r.raise_for_status();assert r.content==raw,(name,'source differs');original.write_bytes(raw)
  else:raw=original.read_bytes();x=parse(raw.decode());url=f'https://gitlab.com/kicad/libraries/kicad-footprints/-/raw/{revision}/{lib}.pretty/{name}.kicad_mod'
  out=clean(x)
  for n in x:
   if isinstance(n,list) and n[0]=='property' and n[1] in ['"Reference"','"Value"']:
    out.append(['fp_text','reference' if n[1]=='"Reference"' else 'value',n[2]]+[e for e in n[3:] if isinstance(e,list) and e[0] in ['at','layer','effects']])
  assert pads(x)==pads(out),name
  path.write_text(dump(out)+'\n');sources[name]={'url':url,'source_sha256':hashlib.sha256(raw).hexdigest(),'method':'Pinned KiCad syntax translation; exact pad numbers/positions/sizes/rotations/shapes/layers/drills preserved','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 elif sources.get(name,{}).get('method','').startswith('Existing'):
  sources[name]={'url':'../glove-v3/electrical/footprints/'+path.name,'method':'Retained V3 footprint with content hash; manufacturer package cited in circuit','sha256':hashlib.sha256(raw).hexdigest()}
(P/'footprint-sources.json').write_text(json.dumps(sources,indent=2)+'\n')
