from pathlib import Path
import pcbnew as k,re,json,math,sys,time
from route_local_fast import route,layers
P=Path(__file__).resolve().parent;src=Path(sys.argv[1]);dst=Path(sys.argv[2]);b=k.LoadBoard(str(src));log=[];deadline=time.monotonic()+600
for rnd in range(2):
 b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(dst),b);k.WriteDRCReport(b,str(P/'local-current.drc.txt'),k.EDA_UNITS_MILLIMETRES,True);s=(P/'local-current.drc.txt').read_text();items=[]
 for bl in s.split('\n['):
  if not bl.startswith('unconnected_items]'):continue
  endpoints=re.findall(r'@\(([-\d.]+) mm, ([-\d.]+) mm\): (.*)',bl)
  if len(endpoints)!=2:continue
  ep=[]
  for x,y,desc in endpoints:
   net=re.search(r'\[(.+?)\]',desc).group(1);al=layers if 'Via ' in desc or ' on *.Cu' in desc else [l for l in layers if b.GetLayerName(l) in desc]
   if not al:break
   ep.append(((float(x),float(y)),al))
  if len(ep)==2:items.append((math.dist(ep[0][0],ep[1][0]),net,ep))
 print('ROUND',rnd,'OPENS',len(items),flush=True)
 for dist,net,ep in sorted(items):
  if time.monotonic()>deadline:break
  ok=route(b,net,*ep[0],*ep[1],step=.10 if rnd==0 else .075,margin=4 if rnd==0 else 8);log.append({'round':rnd,'net':net,'endpoints':ep,'routed':bool(ok)})
  if len(log)%10==0:k.SaveBoard(str(dst),b)
 if time.monotonic()>deadline:break
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());b.SetFileName(str(dst));k.SaveBoard(str(dst),b);dst.with_suffix('.kicad_pro').write_bytes(src.with_suffix('.kicad_pro').read_bytes());k.WriteDRCReport(b,str(dst.with_suffix('.drc.txt')),k.EDA_UNITS_MILLIMETRES,True);dst.with_suffix('.repairs.json').write_text(json.dumps(log,indent=2));print('FINISHED',sum(x['routed'] for x in log),'of',len(log),flush=True)
