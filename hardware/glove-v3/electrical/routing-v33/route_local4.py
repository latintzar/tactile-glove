"""Clearance-conservative outer-copper local repair. KiCad DRC remains authoritative."""
import pcbnew as k, math,heapq,itertools,json
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
mm=k.FromMM; xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));vec=lambda p:k.VECTOR2I(mm(float(p[0])),mm(float(p[1])));layers=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu]
def obstacles(b,net):
 shapes={l:[] for l in layers};holes=[]
 for f in b.GetFootprints():
  for p in f.Pads():
   cx,cy=xy(p.GetPosition());w,h=xy(p.GetSize());a=math.radians(-p.GetOrientationDegrees());c,s=math.cos(a),math.sin(a)
   if p.GetDrillSize().x:holes.append(Point(cx,cy).buffer(max(xy(p.GetDrillSize()))/2+.26+.15))
   if p.GetNetname()==net:continue
   if p.GetShape()==k.PAD_SHAPE_CIRCLE:geom=Point(cx,cy).buffer(w/2)
   elif p.GetShape()==k.PAD_SHAPE_ROUNDRECT:
    r=k.ToMM(p.GetRoundRectCornerRadius());geom=translate(rotate(box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r),-p.GetOrientationDegrees(),origin=(0,0)),cx,cy)
   else:geom=Polygon([(cx+x*c-y*s,cy+x*s+y*c) for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]])
   for l in layers:
    if p.IsOnLayer(l):shapes[l].append(geom)
 for t in b.GetTracks():
  if type(t)==k.PCB_VIA:
   holes.append(Point(xy(t.GetPosition())).buffer(k.ToMM(t.GetDrillValue())/2+.26+.15))
  if t.GetNetname()==net:continue
  if type(t)==k.PCB_VIA:
   geom=Point(xy(t.GetPosition())).buffer(k.ToMM(t.GetWidth())/2)
   for l in layers:shapes[l].append(geom)
  else:shapes[t.GetLayer()].append(LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2))
 keep=box(63,42,73.5,52)
 for l in layers:shapes[l].append(keep)
 obs={l:unary_union(q) for l,q in shapes.items()}
 vobs=unary_union([g.buffer(.465) for g in obs.values()]+holes)
 return {l:g.buffer(.22501) for l,g in obs.items()},vobs

def route(b,net,a,alayers,d,dlayers,step=.10,margin=6):
 obs,vobs=obstacles(b,net);ll=layers
 x0=max(.8,math.floor((min(a[0],d[0])-margin)/step)*step);y0=max(.8,math.floor((min(a[1],d[1])-margin)/step)*step)
 x1=min(89.2,max(a[0],d[0])+margin);y1=min(59.2,max(a[1],d[1])+margin)
 xs=np.arange(x0,x1,step);ys=np.arange(y0,y1,step);nx=len(xs);ny=len(ys);xx,yy=np.meshgrid(xs,ys)
 free=np.array([~shapely.contains_xy(obs[l],xx,yy) for l in ll]);vf=~shapely.contains_xy(vobs,xx,yy)
 def p(n):return (xs[n[1]],ys[n[2]])
 def endpoint(pt,allowed):
  cells={}
  for li,l in enumerate(ll):
   if l not in allowed:continue
   ix=int(round((pt[0]-x0)/step));iy=int(round((pt[1]-y0)/step))
   for x in range(max(0,ix-6),min(nx,ix+7)):
    for y in range(max(0,iy-6),min(ny,iy+7)):
     n=(li,x,y)
     if free[li,y,x] and not LineString([pt,p(n)]).intersects(obs[l]):cells[n]=math.dist(pt,p(n))
  return cells
 starts=endpoint(a,alayers);goals=endpoint(d,dlayers)
 print(net,a,d,'starts/goals',len(starts),len(goals),'grid',nx,ny,flush=True)
 if not starts or not goals:return False
 counter=itertools.count();heap=[];cost=dict(starts);prev={n:None for n in starts};end=None
 def heuristic(n):return math.dist(p(n),d)
 for n,g in starts.items():heapq.heappush(heap,(g+heuristic(n),next(counter),n,g))
 moves=[(dx,dy,math.hypot(dx,dy)*step) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]]
 while heap:
  _,_,n,g=heapq.heappop(heap)
  if g!=cost[n]:continue
  if n in goals:end=n;break
  li,x,y=n
  neighbors=[]
  for dx,dy,c in moves:
   xx1=x+dx;yy1=y+dy
   if 0<=xx1<nx and 0<=yy1<ny and free[li,yy1,xx1] and (not dx or not dy or (free[li,y,xx1] and free[li,yy1,x])):neighbors.append(((li,xx1,yy1),c))
  if vf[y,x]:neighbors.extend(((lj,x,y),4) for lj in range(len(ll)) if lj!=li)
  for nxt,c in neighbors:
   ng=g+c
   if ng>=cost.get(nxt,float('inf')):continue
   cost[nxt]=ng;prev[nxt]=n;heapq.heappush(heap,(ng+heuristic(nxt),next(counter),nxt,ng))
 if end is None:print('no route',len(cost),flush=True);return False
 nodes=[]
 while end is not None:nodes.append(end);end=prev[end]
 nodes.reverse();path=[(nodes[0][0],a)]+[(n[0],p(n)) for n in nodes]+[(nodes[-1][0],d)]
 # Remove collinear intermediate grid points, preserve layer changes.
 simple=[path[0]]
 for i in range(1,len(path)-1):
  l,q=path[i];lp,pp=simple[-1];ln,nn=path[i+1]
  if l==lp==ln and abs((q[0]-pp[0])*(nn[1]-q[1])-(q[1]-pp[1])*(nn[0]-q[0]))<1e-8:continue
  simple.append(path[i])
 simple.append(path[-1]);netobj=b.FindNet(net)
 for (la,pa),(lb,pb) in zip(simple,simple[1:]):
  if la!=lb:
   assert math.dist(pa,pb)<1e-6
   v=k.PCB_VIA(b);v.SetPosition(vec(pa));v.SetWidth(mm(.6));v.SetDrill(mm(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(netobj);b.Add(v)
  elif math.dist(pa,pb)>1e-6:
   assert not LineString([pa,pb]).intersects(obs[ll[la]]),(net,pa,pb,'collision')
   t=k.PCB_TRACK(b);t.SetStart(vec(pa));t.SetEnd(vec(pb));t.SetWidth(mm(.15));t.SetLayer(ll[la]);t.SetNet(netobj);b.Add(t)
 print('routed',net,'length',round(sum(math.dist(pa,pb) for (la,pa),(lb,pb) in zip(simple,simple[1:])),2),'segments',len(simple),flush=True)
 return simple
if __name__=='__main__':
 import sys
 b=k.LoadBoard(sys.argv[1]);report=[]
 repairs=[('3V3A',(44,29.775),[k.F_Cu],(43.3286,33.4012),[k.F_Cu,k.B_Cu]),('GND',(40.3104,27.558),[k.F_Cu],(41.2921,30.8926),[k.F_Cu,k.B_Cu]),('GND',(66.5779,9.7471),[k.F_Cu],(64.1587,17.2758),[k.B_Cu]),('GND',(25,28.225),[k.F_Cu],(29.1708,33.2758),[k.F_Cu,k.B_Cu]),('GND',(11.6576,33.2758),[k.F_Cu,k.B_Cu],(4.2904,33.4346),[k.B_Cu])]
 for r in repairs:
  result=route(b,*r)
  if not result:result=route(b,*r,step=.075,margin=10)
  report.append({'net':r[0],'path':result})
 k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();k.SaveBoard(sys.argv[2],b);open(sys.argv[2]+'.repairs.json','w').write(json.dumps(report,indent=2))
