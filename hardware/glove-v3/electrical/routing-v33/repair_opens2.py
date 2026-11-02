import pcbnew as k,sys,re,json,math
from pathlib import Path
from route_local4 import route,layers
P=Path('/tmp/glove-eda-runtime/power-cad-fix');b=k.LoadBoard(str(P/'local.kicad_pcb'));log=[]
def checks(round):
 k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();k.SaveBoard(str(P/'local.kicad_pcb'),b);k.WriteDRCReport(b,str(P/f'local-{round}.drc.txt'),k.EDA_UNITS_MILLIMETRES,True);return (P/f'local-{round}.drc.txt').read_text()
for rnd in range(2):
 text=checks(rnd);items=[]
 for bl in text.split('\n['):
  if not bl.startswith('unconnected_items]'):continue
  endpoints=re.findall(r'@\(([-\d.]+) mm, ([-\d.]+) mm\): (.*)',bl)
  if len(endpoints)!=2:print('BAD',bl);continue
  v=[]
  for x,y,desc in endpoints:
   net=re.search(r'\[(.+?)\]',desc).group(1);al=layers if 'Via ' in desc or ' on *.Cu' in desc else [l for l in layers if b.GetLayerName(l) in desc]
   if not al:print('BADLAYER',desc);al=layers
   v.append(((float(x),float(y)),al))
  items.append((math.dist(v[0][0],v[1][0]),net,v))
 if not items:break
 print('ROUND',rnd,'OPENS',len(items),flush=True)
 for dist,net,v in sorted(items):
  ok=route(b,net,*v[0],*v[1],step=.075,margin=6+6*rnd)
  log.append({'round':rnd,'net':net,'endpoints':v,'routed':bool(ok)})
  if len(log)%10==0:k.SaveBoard(str(P/'local-in-progress.kicad_pcb'),b)
checks('final');(P/'local-repairs.json').write_text(json.dumps(log,indent=2))
