"""Join filled plane islands with clearance-checked short outer-layer copper bridges.
This operates on a routed candidate. Every accepted result still requires KiCad DRC.
"""
from pathlib import Path
import math,argparse,json
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
import pcbnew as k
P=Path(__file__).parent
ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');args=ap.parse_args()
b=k.LoadBoard(args.input);mm=k.FromMM;vec=lambda p:k.VECTOR2I(mm(p[0]),mm(p[1]));xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));layers=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu]
def linepoly(q):return [xy(q.CPoint(i)) for i in range(q.PointCount())]
def shapes_for_net(net):
 shapes={l:[] for l in layers}
 for f in b.GetFootprints():
  for p in f.Pads():
   if p.GetNetname()==net:continue
   cx,cy=xy(p.GetPosition());w,h=xy(p.GetSize());a=math.radians(-p.GetOrientationDegrees());c,s=math.cos(a),math.sin(a)
   if p.GetShape()==k.PAD_SHAPE_CIRCLE:geom=Point(cx,cy).buffer(w/2)
   else:geom=Polygon([(cx+x*c-y*s,cy+x*s+y*c) for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]])
   for l in layers:
    if p.IsOnLayer(l):shapes[l].append(geom)
 for t in b.GetTracks():
  if t.GetNetname()==net:continue
  if type(t)==k.PCB_VIA:
   geom=Point(*xy(t.GetPosition())).buffer(k.ToMM(t.GetWidth())/2)
   for l in layers:shapes[l].append(geom)
  else:shapes[t.GetLayer()].append(LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2))
 # Rule-area copper keepouts and edge distance are absolute obstacles.
 keep=Polygon([(63,42),(73.5,42),(73.5,52),(63,52)])
 for l in layers:shapes[l].append(keep)
 unions={l:unary_union(v) for l,v in shapes.items()};return unions,unary_union(list(unions.values()))
def sample_geom(g):
 arr=[]
 if g.is_empty:return arr
 polys=[g] if g.geom_type=='Polygon' else list(g.geoms)
 for p in polys:
  if p.area<.03:continue
  ring=p.exterior
  for d in np.arange(0,ring.length,.35):
   q=ring.interpolate(float(d));arr.append((q.x,q.y))
 return arr
report=[]
for layer,net in [(k.In1_Cu,'GND'),(k.In2_Cu,'3V3A')]:
 z=next(z for z in b.Zones() if not z.GetIsRuleArea() and z.GetLayer()==layer);ps=z.GetFilledPolysList(layer)
 polygons=[Polygon(linepoly(ps.COutline(i)),[linepoly(ps.CHole(i,j)) for j in range(ps.HoleCount(i))]).buffer(0) for i in range(ps.OutlineCount())]
 obs,allobs=shapes_for_net(net);nodes=[]
 # Drill spacing also applies to same-net vias.
 hole_centres=[xy(t.GetPosition()) for t in b.GetTracks() if type(t)==k.PCB_VIA]
 hole_obstacles=unary_union([Point(p).buffer(.56) for p in hole_centres])
 for i,poly in enumerate(polygons):
  pts=[p for p in sample_geom(poly.buffer(-.35)) if .85<p[0]<89.15 and .85<p[1]<59.15 and not Point(p).buffer(.475).intersects(allobs) and not Point(p).intersects(hole_obstacles)]
  nodes.append(pts)
 print(net,'islands',len(polygons),'via candidates',[len(p) for p in nodes],flush=True)
 joined={max(range(len(polygons)),key=lambda i:polygons[i].area)};remaining=set(range(len(polygons)))-joined
 while remaining:
  targets=[(p,i) for i in joined for p in nodes[i]]
  if not targets:break
  tree=cKDTree([p for p,i in targets]);candidates=[]
  for i in remaining:
   for a in nodes[i]:
    ds,ix=tree.query(a,k=min(12,len(targets)))
    for dist,j in zip(np.atleast_1d(ds),np.atleast_1d(ix)):
     if dist>18:continue
     d=targets[int(j)][0];candidates.append((float(dist),i,a,d))
  candidates.sort();chosen=None
  for length,i,a,d in candidates:
   if any(math.dist(p,q)<.56 for p in (a,d) for q in hole_centres):continue
   for l in (k.F_Cu,k.B_Cu):
    paths=[[a,d],[a,(a[0],d[1]),d],[a,(d[0],a[1]),d]]
    for path in paths:
     if not LineString(path).buffer(.25).intersects(obs[l]):chosen=(i,a,d,l,path);break
    if chosen:break
   if chosen:break
  if not chosen:print('No direct bridge for',net,remaining,flush=True);break
  i,a,d,l,path=chosen
  n=b.FindNet(net)
  for pt in (a,d):
   v=k.PCB_VIA(b);v.SetPosition(vec(pt));v.SetWidth(mm(.6));v.SetDrill(mm(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(n);b.Add(v)
  for p,q in zip(path,path[1:]):
   if p==q:continue
   t=k.PCB_TRACK(b);t.SetStart(vec(p));t.SetEnd(vec(q));t.SetWidth(mm(.15));t.SetLayer(l);t.SetNet(n);b.Add(t)
  hole_centres.extend((a,d));joined.add(i);remaining.remove(i);report.append({'net':net,'layer':b.GetLayerName(l),'path_mm':path});print('bridged',net,i,'length',round(LineString(path).length,2),'remaining',len(remaining),flush=True)
 k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity()
k.SaveBoard(args.output,b);Path(args.output+'.stitches.json').write_text(json.dumps(report,indent=2));print('saved',args.output,flush=True)
