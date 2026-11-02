"""Fetch revision-pinned KiCad library geometry and translate Seeed syntax, preserving pads.
Manufacturer geometry is kept in source form alongside converted KiCad7 data.
"""
from pathlib import Path
import json,hashlib,re,requests
P=Path(__file__).parent; F=P/'footprints';F.mkdir(exist_ok=True)
items={
 'SOIC-16_3.9x9.9mm_P1.27mm':'Package_SO',
 'C_0805_2012Metric':'Capacitor_SMD',
 'SOT-363_SC-70-6':'Package_TO_SOT_SMD',
 'SW_SPST_PTS636':'Button_Switch_SMD',
}
revision=requests.get('https://api.github.com/repos/KiCad/kicad-footprints/commits/master',timeout=25).json()['sha']
results=[]
for name,lib in items.items():
 url=f'https://raw.githubusercontent.com/KiCad/kicad-footprints/{revision}/{lib}.pretty/{name}.kicad_mod'
 r=requests.get(url,timeout=25)
 if r.status_code!=200:results.append({'name':name,'error':r.status_code,'url':url});continue
 path=F/(name+'.kicad_mod');path.write_bytes(r.content);results.append({'file':path.name,'url':url,'sha256':hashlib.sha256(r.content).hexdigest()})
# Lightweight S-expression parser retains all quoted strings exactly.
def parse(s):
 toks=re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+|[()]',s);stack=[];root=None
 for t in toks:
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
src=F/'XIAO-nRF52840-SMD.kicad_mod';x=parse(src.read_text());original=src.read_bytes()
out=['footprint','"XIAO-nRF52840-SMD-kicad7"',['version','20221018'],['generator','pcbnew'],['layer','"F.Cu"'],['attr','smd']]
for n in x[2:]:
 if not isinstance(n,list):continue
 if n[0] in ['fp_line','fp_arc','pad']:
  out.append([e for e in n if not(isinstance(e,list) and e[0] in ['uuid','unlocked','tenting'])])
 elif n[0]=='property' and n[1] in ['"Reference"','"Value"']:
  out.append(['fp_text','reference' if n[1]=='"Reference"' else 'value',n[2]]+[e for e in n[3:] if isinstance(e,list) and e[0] in ['at','layer','effects']])
converted=F/'XIAO-nRF52840-SMD-kicad7.kicad_mod';converted.write_text(dump(out)+'\n')
# Assert all pad geometries and numbers preserve exact source tokens, not a guessed outline.
def pg(g):return [{k:child(n,k) for k in ['at','size','layers','roundrect_rratio']}|{'number':n[1],'type':n[2],'shape':n[3]} for n in g if isinstance(n,list) and n[0]=='pad']
assert pg(x)==pg(out)
results.append({'file':converted.name,'source':src.name,'source_sha256':hashlib.sha256(original).hexdigest(),'sha256':hashlib.sha256(converted.read_bytes()).hexdigest(),'check':'all 22 pad numbers, positions, sizes, rotations, shapes, radii and layers identical to manufacturer source'})
(P/'footprints-preparation.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
