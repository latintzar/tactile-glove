from pathlib import Path
import pcbnew as k,re,math,json
from route_local4 import xy
P=Path('/tmp/glove-eda-runtime/power-cad-fix');b=k.LoadBoard(str(P/'local.kicad_pcb'));retained=[];log=[]
for rnd in range(30):
 k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();k.WriteDRCReport(b,str(P/'clean.drc.txt'),k.EDA_UNITS_MILLIMETRES,True);s=(P/'clean.drc.txt').read_text();tracks=list(b.GetTracks());retained+=tracks;remove={}
 for bl in s.split('\n['):
  if not bl.startswith(('track_dangling]','via_dangling]')):continue
  m=re.search(r'@\(([-\d.]+) mm, ([-\d.]+) mm\): (?:Track|Via) \[(.*?)\](.*)',bl);assert m,bl
  x,y,net,tail=m.groups();pt=(float(x),float(y));candidates=[]
  for t in tracks:
   if t.GetNetname()!=net:continue
   if type(t)==k.PCB_VIA:
    if bl.startswith('via_dangling]') and math.dist(xy(t.GetPosition()),pt)<.0002:candidates.append(t)
   elif bl.startswith('track_dangling]') and b.GetLayerName(t.GetLayer()) in tail and min(math.dist(xy(t.GetStart()),pt),math.dist(xy(t.GetEnd()),pt))<.0002:
    length=float(re.search(r'length ([\d.]+) mm',tail).group(1))
    if abs(k.ToMM(t.GetLength())-length)<.0002:candidates.append(t)
  if len(candidates)!=1:print('ambiguous',len(candidates),bl[:180],flush=True)
  for t in candidates:remove[t.m_Uuid.AsString()]=t
 print('CLEANUP',rnd,'remove',len(remove),flush=True)
 if not remove:break
 for t in remove.values():log.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'round':rnd});b.Remove(t)
k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();k.SaveBoard(str(P/'local.kicad_pcb'),b);k.WriteDRCReport(b,str(P/'clean.drc.txt'),k.EDA_UNITS_MILLIMETRES,True);(P/'stub-cleanup.json').write_text(json.dumps(log,indent=2))
