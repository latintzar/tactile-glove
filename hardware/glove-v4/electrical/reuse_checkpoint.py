from pathlib import Path
from collections import defaultdict,Counter
import pcbnew as k,json,math
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
P=Path(__file__).resolve().parent;mm=k.FromMM;xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y))
b=k.LoadBoard(str(P/'glove-v4-prepared.kicad_pcb'));old=k.LoadBoard(str(P/'route-checkpoint.kicad_pcb'))
def endpoints(board):
 out=defaultdict(list)
 for f in board.GetFootprints():
  for p in f.Pads():out[p.GetNetname()].append((f.GetReference(),p.GetNumber(),p.GetPosition().x,p.GetPosition().y,p.GetLayer()))
 return {n:sorted(v) for n,v in out.items()}
a,z=endpoints(b),endpoints(old);changed={n for n in a if a[n]!=z.get(n)};shared={'GND','3V3_SYS','3V3_A','VBAT','VSYS','VMID1V25','VREF3V0','VEXC2V5','1V8'};reuse=set(a)-changed|shared
for t in list(b.GetTracks()):
 if t.GetNetname() in reuse:b.RemoveNative(t)
count=0;widened=0
for t in old.GetTracks():
 if t.GetNetname() not in reuse:continue
 q=t.Duplicate();q.SetNet(b.FindNet(t.GetNetname()))
 if type(q)!=k.PCB_VIA and q.GetWidth()<mm(.15):q.SetWidth(mm(.15));widened+=1
 b.Add(q);count+=1
def pg(p):
 x,y=xy(p.GetPosition());w,h=xy(p.GetSize())
 if p.GetShape()==k.PAD_SHAPE_CIRCLE:return Point(x,y).buffer(w/2)
 if p.GetShape()==k.PAD_SHAPE_ROUNDRECT:
  r=k.ToMM(p.GetRoundRectCornerRadius());g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r)
 else:g=box(-w/2,-h/2,w/2,h/2)
 return translate(rotate(g,-p.GetOrientationDegrees(),origin=(0,0)),x,y)
pads=[(p,pg(p)) for f in b.GetFootprints() for p in f.Pads()];tree=STRtree([s for p,s in pads]);removed=[]
for t in list(b.GetTracks()):
 via=type(t)==k.PCB_VIA;g=Point(xy(t.GetPosition())) if via else LineString([xy(t.GetStart()),xy(t.GetEnd())]);rad=k.ToMM(t.GetWidth())/2
 for i in tree.query(g.buffer(rad+.7)):
  p,shape=pads[int(i)]
  if not via and not p.IsOnLayer(t.GetLayer()):continue
  if p.GetNetname()!=t.GetNetname() and g.distance(shape)<rad+.14999:
   removed.append(t.GetNetname());b.RemoveNative(t);break
  if via and p.GetDrillSize().x and math.dist(xy(t.GetPosition()),xy(p.GetPosition()))<k.ToMM(t.GetDrillValue()+p.GetDrillSize().x)/2+.24999:
   removed.append(t.GetNetname());b.RemoveNative(t);break
b.SetFileName(str(P/'glove-v4-repair.kicad_pcb'));b.GetDesignSettings().m_MinThroughDrill=mm(.2);b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(b.GetFileName(),b)
(P/'glove-v4-repair.kicad_pro').write_bytes((P/'glove-v4-prepared.kicad_pro').read_bytes());k.WriteDRCReport(b,str(P/'repair-drc.txt'),k.EDA_UNITS_MILLIMETRES,True)
print(json.dumps({'changed_nets':sorted(changed),'reused_items':count,'widened_necks':widened,'removed_pad_conflicts':Counter(removed)}),flush=True)
