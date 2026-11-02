"""Clearance-conservative outer-copper local repair. KiCad DRC remains authoritative."""
import pcbnew as k, math,heapq,itertools,json,time
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
SOFT_ALLOWED=set()
SOFT_OPEN_TARGETS=set()
mm=k.FromMM; xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));vec=lambda p:k.VECTOR2I(mm(float(p[0])),mm(float(p[1])));layers=[k.F_Cu,k.In2_Cu,k.In5_Cu,k.B_Cu]
def obstacles(b,net,bounds):
 from routing_layers import assert_stack
 assert_stack(b)
 x0,y0,x1,y1=bounds
 def outside(q):
  z=q.GetBoundingBox();return k.ToMM(z.GetRight())<x0-.6 or k.ToMM(z.GetLeft())>x1+.6 or k.ToMM(z.GetBottom())<y0-.6 or k.ToMM(z.GetTop())>y1+.6
 shapes={l:[] for l in layers};holes=[];soft=[]
 for f in b.GetFootprints():
  for p in f.Pads():
   if outside(p):continue
   cx,cy=xy(p.GetPosition());w,h=xy(p.GetSize());a=math.radians(-p.GetOrientationDegrees());c,s=math.cos(a),math.sin(a)
   if p.GetDrillSize().x:holes.append(Point(cx,cy).buffer(max(xy(p.GetDrillSize()))/2+.251+.10))
   if p.GetAttribute()==k.PAD_ATTRIB_NPTH:
    hole=Point(cx,cy).buffer(max(xy(p.GetDrillSize()))/2)
    holes.append(hole.buffer(.485))
    for l in layers:shapes[l].append(hole.buffer(.10))
    continue
   if p.GetNetname()==net:continue
   if p.GetShape()==k.PAD_SHAPE_CUSTOM:
    bb=p.GetBoundingBox();geom=box(k.ToMM(bb.GetLeft()),k.ToMM(bb.GetTop()),k.ToMM(bb.GetRight()),k.ToMM(bb.GetBottom()))
   elif p.GetShape()==k.PAD_SHAPE_CIRCLE:geom=Point(cx,cy).buffer(w/2)
   elif p.GetShape()==k.PAD_SHAPE_ROUNDRECT:
    r=k.ToMM(p.GetRoundRectCornerRadius());geom=translate(rotate(box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r),-p.GetOrientationDegrees(),origin=(0,0)),cx,cy)
   else:geom=Polygon([(cx+x*c-y*s,cy+x*s+y*c) for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]])
   for l in layers:
    if p.IsOnLayer(l):shapes[l].append(geom)
 for t in b.GetTracks():
  if outside(t):continue
  if type(t)==k.PCB_VIA:
   holes.append(Point(xy(t.GetPosition())).buffer(k.ToMM(t.GetDrillValue())/2+.251+.10))
  if t.GetNetname()==net:continue
  if type(t)!=k.PCB_VIA and t.GetWidth()<mm(.25) and t.GetNetname() in SOFT_ALLOWED and t.GetLayer() in layers and (t.GetNetname() in SOFT_OPEN_TARGETS or k.ToMM(t.GetLength())<3):
   soft.append((t,LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2)))
   continue
  if type(t)==k.PCB_VIA:
   geom=Point(xy(t.GetPosition())).buffer(k.ToMM(t.GetWidth())/2)
   for l in layers:shapes[l].append(geom)
  elif t.GetLayer() in shapes:shapes[t.GetLayer()].append(LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2))
 for z in b.Zones():
  if not z.GetIsRuleArea():continue
  o=z.Outline()
  for i in range(o.OutlineCount()):
   q=o.COutline(i);geom=Polygon([xy(q.CPoint(j)) for j in range(q.PointCount())])
   if z.GetDoNotAllowVias():holes.append(geom.buffer(.225))
   if z.GetDoNotAllowTracks():
    for l in layers:
     if z.GetLayerSet().Contains(l):shapes[l].append(geom)
 obs={l:unary_union(q) for l,q in shapes.items()}
 vobs=unary_union([g.buffer(.351) for g in obs.values()]+holes)
 return {l:g.buffer(.226) for l,g in obs.items()},vobs,soft

def route(b,net,a,alayers,d,dlayers,step=.10,margin=6,extra_a=None,extra_d=None):
 ll=layers
 aa=extra_a or [(a,alayers)];dd=extra_d or [(d,dlayers)];pts=[p for p,l in aa+dd]
 x0=max(.8,math.floor((min(p[0] for p in pts)-margin)/step)*step);y0=max(.8,math.floor((min(p[1] for p in pts)-margin)/step)*step)
 x1=min(99.2,max(p[0] for p in pts)+margin);y1=min(79.2,max(p[1] for p in pts)+margin)
 obs,vobs,soft=obstacles(b,net,(x0,y0,x1,y1))
 xs=np.arange(x0,x1,step);ys=np.arange(y0,y1,step);nx=len(xs);ny=len(ys);xx,yy=np.meshgrid(xs,ys)
 free=np.array([~shapely.contains_xy(obs[l],xx,yy) for l in ll]);vf=~shapely.contains_xy(vobs,xx,yy)
 soft_grid=np.array([shapely.contains_xy(unary_union([g.buffer(.226) for t,g in soft if t.GetLayer()==l]),xx,yy) for l in ll]);soft_vias=np.any(soft_grid,axis=0)
 def p(n):return (xs[n[1]],ys[n[2]])
 def endpoint(pt,allowed):
  cells={}
  for li,l in enumerate(ll):
   if l not in allowed:continue
   ix=int(round((pt[0]-x0)/step));iy=int(round((pt[1]-y0)/step))
   for x in range(max(0,ix-2),min(nx,ix+3)):
    for y in range(max(0,iy-2),min(ny,iy+3)):
     n=(li,x,y)
     if free[li,y,x] and not LineString([pt,p(n)]).intersects(obs[l]):cells[n]=math.dist(pt,p(n))
  return cells
 starts={};goals={};start_pts={};goal_pts={}
 for pt,allowed in aa:
  for n,c in endpoint(pt,allowed).items():
   if c<starts.get(n,1e9):starts[n]=c;start_pts[n]=pt
 for pt,allowed in dd:
  for n,c in endpoint(pt,allowed).items():
   if c<goals.get(n,1e9):goals[n]=c;goal_pts[n]=pt
 print(net,a,d,'starts/goals',len(starts),len(goals),'grid',nx,ny,flush=True)
 if not starts or not goals:return False
 counter=itertools.count();heap=[];cost=dict(starts);prev={n:None for n in starts};end=None
 from scipy.spatial import cKDTree
 dt=cKDTree([pt for pt,l in dd]);hc=np.asarray(dt.query(np.column_stack([xx.ravel(),yy.ravel()]))[0]).reshape(xx.shape)
 def heuristic(n):return hc[n[2],n[1]]
 for n,g in starts.items():heapq.heappush(heap,(g+1.5*heuristic(n),next(counter),n,g))
 moves=[(dx,dy,math.hypot(dx,dy)*step) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]]
 deadline=time.monotonic()+25
 while heap:
  if len(cost)>600000 or time.monotonic()>deadline:print("bounded search exhausted",flush=True);return False
  _,_,n,g=heapq.heappop(heap)
  if g!=cost[n]:continue
  if n in goals:end=n;break
  li,x,y=n
  neighbors=[]
  for dx,dy,c in moves:
   xx1=x+dx;yy1=y+dy
   if 0<=xx1<nx and 0<=yy1<ny and free[li,yy1,xx1] and (not dx or not dy or (free[li,y,xx1] and free[li,yy1,x])):neighbors.append(((li,xx1,yy1),c*(1+40*soft_grid[li,yy1,xx1])))
  if vf[y,x]:neighbors.extend(((lj,x,y),4+30*soft_vias[y,x]) for lj in range(len(ll)) if lj!=li)
  for nxt,c in neighbors:
   ng=g+c
   if ng>=cost.get(nxt,float('inf')):continue
   cost[nxt]=ng;prev[nxt]=n;heapq.heappush(heap,(ng+1.5*heuristic(nxt),next(counter),nxt,ng))
 if end is None:print('no route',len(cost),flush=True);return False
 goal_point=goal_pts[end];nodes=[]
 while end is not None:nodes.append(end);end=prev[end]
 nodes.reverse();path=[(nodes[0][0],start_pts[nodes[0]])]+[(n[0],p(n)) for n in nodes]+[(nodes[-1][0],goal_point)]
 # Remove collinear intermediate grid points, preserve layer changes.
 simple=[path[0]]
 for i in range(1,len(path)-1):
  l,q=path[i];lp,pp=simple[-1];ln,nn=path[i+1]
  if l==lp==ln and abs((q[0]-pp[0])*(nn[1]-q[1])-(q[1]-pp[1])*(nn[0]-q[0]))<1e-8:continue
  simple.append(path[i])
 simple.append(path[-1]);netobj=b.FindNet(net)
 for (la,pa),(lb,pb) in zip(simple,simple[1:]):
  if la==lb and math.dist(pa,pb)>1e-6 and LineString([pa,pb]).intersects(obs[ll[la]]):
   print('Rejected interpolated edge collision',net,flush=True);return False
 touched={};newshapes={l:[] for l in ll}
 for (la,pa),(lb,pb) in zip(simple,simple[1:]):
  if la!=lb:
   for l in ll:newshapes[l].append(Point(pa).buffer(.200+.151))
  elif math.dist(pa,pb)>1e-6:newshapes[ll[la]].append(LineString([pa,pb]).buffer(.075+.15001))
 newshapes={l:unary_union(gs) for l,gs in newshapes.items()}
 for t,g in soft:
  if g.intersects(newshapes[t.GetLayer()]):touched[t.m_Uuid.AsString()]=t
 nets=set(t.GetNetname() for t in touched.values())
 if len(nets)>2 or len(touched)>12:print('Rejected excessive displacement',len(touched),nets,flush=True);return False
 for t in touched.values():b.RemoveNative(t)
 if touched:print('DISPLACED',net,len(touched),sorted(nets),flush=True)
 for (la,pa),(lb,pb) in zip(simple,simple[1:]):
  if la!=lb:
   assert math.dist(pa,pb)<1e-6
   v=k.PCB_VIA(b);v.SetPosition(vec(pa));v.SetWidth(mm(.4));v.SetDrill(mm(.2));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(netobj);b.Add(v)
  elif math.dist(pa,pb)>1e-6:
   assert not LineString([pa,pb]).intersects(obs[ll[la]]),(net,pa,pb,'collision')
   t=k.PCB_TRACK(b);t.SetStart(vec(pa));t.SetEnd(vec(pb));t.SetWidth(mm(.15));t.SetLayer(ll[la]);t.SetNet(netobj);b.Add(t)
 print('routed',net,'length',round(sum(math.dist(pa,pb) for (la,pa),(lb,pb) in zip(simple,simple[1:])),2),'segments',len(simple),flush=True)
 return simple
