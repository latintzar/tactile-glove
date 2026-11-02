from pathlib import Path
import pcbnew as k,math,json
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
from shapely.strtree import STRtree
from route_local4 import obstacles,xy,vec,mm,layers
P=Path('/tmp/glove-eda-runtime/power-cad-fix');b=k.LoadBoard(str(P/'local.kicad_pcb'));log=[]
old=json.loads((P/'escape-log.json').read_text())
retained=list(b.GetTracks())
starts={'3V3A':(58.95,41.5),'VEXC2V5':(56.5,55.825),'CHG_IN_R3':(39.825,14.0)}
for r in old:
 for t in retained:
  if t.GetNetname()!=r['net']:continue
  if type(t)==k.PCB_VIA and math.dist(xy(t.GetPosition()),r['via'])<1e-5:b.Remove(t)
  elif type(t)==k.PCB_TRACK and math.dist(xy(t.GetStart()),starts[r['net']])<1e-5 and math.dist(xy(t.GetEnd()),r['via'])<1e-5:b.Remove(t)
 for q in r['removed']:
  t=k.PCB_TRACK(b);t.SetStart(vec(q['a']));t.SetEnd(vec(q['b']));t.SetWidth(mm(.15));t.SetLayer(b.GetLayerID(q['layer']));t.SetNet(b.FindNet(q['net']));b.Add(t)
def ps(p):
 x,y=xy(p.GetPosition());w,h=xy(p.GetSize());r=k.ToMM(p.GetRoundRectCornerRadius()) if p.GetShape()==k.PAD_SHAPE_ROUNDRECT else 0
 if p.GetShape()==k.PAD_SHAPE_CIRCLE:return Point(x,y).buffer(w/2)
 g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r) if r else box(-w/2,-h/2,w/2,h/2)
 return translate(rotate(g,-p.GetOrientationDegrees(),origin=(0,0)),x,y)
for net,a,layer in [('3V3A',(58.95,41.5),k.F_Cu),('VEXC2V5',(56.5,55.825),k.B_Cu),('CHG_IN_R3',(39.825,14.0),k.F_Cu)]:
 obs,_=obstacles(b,net);pads=[ps(p).buffer(.451 if p.GetNetname()!=net else .20) for f in b.GetFootprints() for p in f.Pads()];holes=[Point(xy(t.GetPosition())).buffer(.751 if t.GetNetname()!=net else .56) for t in b.GetTracks() if type(t)==k.PCB_VIA];holes += [Point(xy(p.GetPosition())).buffer(k.ToMM(p.GetDrillSize().x)/2+.41) for f in b.GetFootprints() for p in f.Pads() if p.GetDrillSize().x];padlayer=[ps(p).buffer(.226) for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()!=net and p.IsOnLayer(layer)];padlayer += [Point(xy(t.GetPosition())).buffer(.526) for t in b.GetTracks() if type(t)==k.PCB_VIA and t.GetNetname()!=net];tracks=[t for t in b.GetTracks() if type(t)==k.PCB_TRACK and t.GetNetname()!=net];geoms=[LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2+.451) for t in tracks];best=None
 vp=unary_union(pads+holes);pl=unary_union(padlayer);tr=STRtree(geoms)
 tl=[LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(.15+k.ToMM(t.GetWidth())/2+.075) if t.GetLayer()==layer else Point(-100,-100) for t in tracks];ts=STRtree(tl)
 for ix in range(-35,36):
  for iy in range(-35,36):
   q=(a[0]+ix*.1,a[1]+iy*.1);g=Point(q)
   if not .8<q[0]<89.2 or not .8<q[1]<59.2 or math.dist(q,a)>.0+3.5:continue
   if g.intersects(vp) or LineString([a,q]).intersects(pl):continue
   line=LineString([a,q]);indices=set(int(i) for i in tr.query(g) if g.intersects(geoms[int(i)]));indices.update(int(i) for i in ts.query(line) if line.intersects(tl[int(i)]));conflicts=[tracks[i] for i in indices];score=len(conflicts)*5+math.dist(a,q)
   if best is None or score<best[0]:best=(score,q,conflicts)
 assert best,net
 _,q,removed=best
 for t in removed:b.Remove(t)
 v=k.PCB_VIA(b);v.SetPosition(vec(q));v.SetWidth(mm(.6));v.SetDrill(mm(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));b.Add(v)
 t=k.PCB_TRACK(b);t.SetStart(vec(a));t.SetEnd(vec(q));t.SetWidth(mm(.15));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)
 log.append({'net':net,'via':q,'removed':[{'net':t.GetNetname(),'a':xy(t.GetStart()),'b':xy(t.GetEnd()),'layer':b.GetLayerName(t.GetLayer())} for t in removed]});print(log[-1],flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();k.SaveBoard(str(P/'local.kicad_pcb'),b);k.WriteDRCReport(b,str(P/'escape.drc.txt'),k.EDA_UNITS_MILLIMETRES,True);(P/'escape-log.json').write_text(json.dumps(log,indent=2))
