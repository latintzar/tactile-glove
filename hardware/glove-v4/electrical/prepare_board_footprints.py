from pathlib import Path
import json,shutil,requests,re,hashlib
ROOT=next(a for a in Path(__file__).resolve().parents if (a / 'hardware/glove-v4').is_dir()) / 'hardware';P=Path(__file__).resolve().parent;F=P/'footprints';F.mkdir(exist_ok=True)
parts=json.loads((ROOT/'glove-v4/electrical/components.json').read_text())['components'];rev='f8440fa61a5690b48b325c891fdb99c0038a5a59'
def parse(s):
 stack=[]
 for t in re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+|[()]',s):
  if t=='(':
   n=[]
   if stack:stack[-1].append(n)
   else:root=n
   stack.append(n)
  elif t==')':stack.pop()
  else:stack[-1].append(t)
 return root
def dump(x):return '('+' '.join(dump(v) if isinstance(v,list) else v for v in x)+')'
def clean(n):
 if not isinstance(n,list):return n
 if n and n[0] in ['uuid','generator_version','unlocked','tenting','remove_unused_layers','embedded_fonts','duplicate_pad_numbers_are_jumpers','placement']:return None
 if n and n[0]=='property':return None
 if n and n[0]=='version':return ['version','20221018']
 if n and n[0]=='fill' and len(n)==2 and n[1] in ['yes','no']:return ['fill','solid' if n[1]=='yes' else 'none']
 return [v for e in n if (v:=clean(e)) is not None]
out=[]
for fp in sorted({p['footprint'] for p in parts}):
 lib,n=fp.split(':');dst=F/(n+'.kicad_mod')
 found=next((z for parent in ['glove-v4/interfaces','glove-v4/power','glove-v3/electrical'] if (z:=ROOT/parent/'footprints'/dst.name).exists()),None)
 if found:raw=found.read_bytes();source=str(found.relative_to(ROOT))
 else:
  source=f'https://gitlab.com/kicad/libraries/kicad-footprints/-/raw/{rev}/{lib}.pretty/{dst.name}';r=requests.get(source,timeout=20);r.raise_for_status();raw=r.content
 x=parse(raw.decode());y=clean(x)
 for z in x:
  if isinstance(z,list) and z[0]=='property' and z[1] in ['"Reference"','"Value"']:y.append(['fp_text','reference' if z[1]=='"Reference"' else 'value',z[2]]+[e for e in z[3:] if isinstance(e,list) and e[0] in ['at','layer','effects']])
 dst.write_text(dump(y)+'\n');out.append({'name':n,'source':source,'source_sha256':hashlib.sha256(raw).hexdigest(),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
(P/'footprint-sources.json').write_text(json.dumps(out,indent=2)+'\n');print(len(out),'footprints')
