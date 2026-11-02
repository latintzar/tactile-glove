from pathlib import Path
import pcbnew as k,math,json
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
from route_local4 import obstacles,xy,vec,mm,layers
P=Path('/tmp/glove-eda-runtime/power-cad-fix');b=k.LoadBoard(str(P/'local.kicad_pcb'));log=[]
def ps(p):
 x,y=xy(p.GetPosition());w,h=xy(p.GetSize());r=k.ToMM(p.GetRoundRectCornerRadius()) if p.GetShape()==k.PAD_SHAPE_ROUNDRECT else 0
 if p.GetShape()==k.PAD_SHAPE_CIRCLE:return Point(x,y).buffer(w/2)
 g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r) if r else box(-w/2,-h/2,w/2,h/2)
 return translate(rotate(g,-p.GetOrientationDegrees(),origin=(0,0)),x,y)
for net,a,layer in [('3V3A',(58.95,41.5),k.F_Cu),('VEXC2V5',(56.5,55.825),k.B_Cu),('CHG_IN_R3',(39.825,14.0),k.F_Cu)]:
 obs,_=obstacles(b,net);pads=[ps(p).buffer(.451) for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()!=net];holes=[Point(xy(t.GetPosition())).buffer(.56) for t in b.GetTracks() if type(t)==k.PCB_VIA];holes += [Point(xy(p.GetPosition())).buffer(k.ToMM(p.GetDrillSize().x)/2+.41) for f in b.GetFootprints() for p in f.Pads() if p.GetDrillSize().x];tracks=[t for t in b.GetTracks() if type(t)==k.PCB_TRACK and t.GetNetname()!=net];geoms=[LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2+.451) for t in tracks];best=None
 for ix in range(-35,36):
  for iy in range(-35,36):
   q=(a[0]+ix*.1,a[1]+iy*.1);g=Point(q)
   if not .8<q[0]<89.2 or not .8<q[1]<59.2 or math.dist(q,a)>.0+3.5:continue
   if any(g.intersects(o) for o in pads+holes) or LineString([a,q]).intersects(obs[layer]):continue
   conflicts=[t for t,tg in zip(tracks,geoms) if g.intersects(tg)];score=len(conflicts)*5+math.dist(a,q)
   if best is None or score<best[0]:best=(score,q,conflicts)
 assert best,net
 _,q,removed=best
 for t in removed:b.Remove(t)
 v=k.PCB_VIA(b);v.SetPosition(vec(q));v.SetWidth(mm(.6));v.SetDrill(mm(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));b.Add(v)
 t=k.PCB_TRACK(b);t.SetStart(vec(a));t.SetEnd(vec(q));t.SetWidth(mm(.15));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)
 log.append({'net':net,'via':q,'removed':[{'net':t.GetNetname(),'a':xy(t.GetStart()),'b':xy(t.GetEnd()),'layer':b.GetLayerName(t.GetLayer())} for t in removed]});print(log[-1],flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();k.SaveBoard(str(P/'local.kicad_pcb'),b);k.WriteDRCReport(b,str(P/'escape.drc.txt'),k.EDA_UNITS_MILLIMETRES,True);(P/'escape-log.json').write_text(json.dumps(log,indent=2))
