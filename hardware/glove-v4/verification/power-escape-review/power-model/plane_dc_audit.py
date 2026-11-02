"""Conservative 2D resistive-sheet approximation with strict terminal validation."""
import pcbnew as k,sys,json,time,math
from pathlib import Path
import numpy as np,shapely
from shapely.geometry import Polygon,Point
from scipy.sparse import coo_matrix,diags
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve
src=Path(sys.argv[1]);out=Path(sys.argv[2]);step=float(sys.argv[3]) if len(sys.argv)>3 else .1;config=json.loads(Path(sys.argv[4]).read_text()) if len(sys.argv)>4 else {};validate_only='--validate-only' in sys.argv
b=k.LoadBoard(str(src));xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));net_name=config.get('net')
if not net_name or net_name not in b.GetNetsByName(): raise ValueError(f"terminal net is missing from board: {net_name!r}")
# Select the actual largest filled polygon, retaining its owning zone/layer.
zone_polys=[]
for z in b.Zones():
 if z.GetIsRuleArea() or z.GetNetname()!=net_name or (config.get('layer') and b.GetLayerName(z.GetLayer())!=config['layer']): continue
 q=z.GetFilledPolysList(z.GetLayer())
 for i in range(q.OutlineCount()):
  o=q.COutline(i); holes=[]
  for h in range(q.HoleCount(i)):
   a=q.CHole(i,h); holes.append([xy(a.CPoint(j)) for j in range(a.PointCount())])
  zone_polys.append((z,Polygon([xy(o.CPoint(j)) for j in range(o.PointCount())],holes)))
if not zone_polys: raise ValueError(f"no filled zone for terminal net {net_name!r} on requested layer {config.get('layer')!r}")
zone,g=max(zone_polys,key=lambda zg:zg[1].area); zone_layer_id=zone.GetLayer(); zone_layer_name=b.GetLayerName(zone_layer_id)
if config.get('layer') and zone_layer_name!=config['layer']: raise ValueError(f"selected zone layer mismatch: {zone_layer_name!r}")
source_xy=config.get('sources',[(30.3,67.2),(31.1,67.2)]); load_xy=config.get('loads',[(98.5,77.24),(97.2879,77.5467)])
for role,pts in (("source",source_xy),("load",load_xy)):
 if not pts: raise ValueError(f"missing {role} terminals")
 for pt in pts:
  if len(pt)!=2 or not all(math.isfinite(float(v)) for v in pt): raise ValueError(f"nonfinite {role} terminal: {pt!r}")
  if not g.covers(Point(float(pt[0]),float(pt[1]))): raise ValueError(f"{role} terminal {pt} is outside filled {net_name} zone on {zone_layer_name}")
terminal_items=[]
for t in b.GetTracks():
 if t.GetNetname()==net_name and t.Type()==k.PCB_VIA_T and t.GetLayerSet().Contains(zone_layer_id): terminal_items.append((k.ToMM(t.GetPosition().x),k.ToMM(t.GetPosition().y),'via'))
for f in b.GetFootprints():
 for pad in f.Pads():
  if pad.GetNetname()==net_name and pad.IsOnLayer(zone_layer_id):
   q=pad.GetPosition(); terminal_items.append((k.ToMM(q.x),k.ToMM(q.y),f"pad:{f.GetReference()}:{pad.GetNumber()}"))
if not terminal_items: raise ValueError(f"no board terminals for {net_name!r} on {zone_layer_name}")
for role,pts in (("source",source_xy),("load",load_xy)):
 for x,y in pts:
  if min(math.hypot(float(x)-a,float(y)-bb) for a,bb,_ in terminal_items)>0.02: raise ValueError(f"{role} terminal ({x},{y}) has no matching {net_name} pad/via on {zone_layer_name}")
if validate_only:
 print(json.dumps({'board_sha256':__import__('hashlib').sha256(src.read_bytes()).hexdigest(),'net':net_name,'layer':zone_layer_name,'sources':source_xy,'loads':load_xy,'validated':True},indent=2)); raise SystemExit(0)
xs=np.arange(.5,99.5,step);ys=np.arange(.5,79.5,step);xx,yy=np.meshgrid(xs,ys);mask=shapely.contains_xy(g,xx,yy);ids=np.full(mask.shape,-1,dtype=np.int32);ids[mask]=np.arange(mask.sum());pairs=[]
for a,d in [(ids[:,:-1],ids[:,1:]),(ids[:-1,:],ids[1:,:])]:
 good=(a>=0)&(d>=0);pairs.append((a[good],d[good]))
aa=np.concatenate([a for a,d in pairs]);dd=np.concatenate([d for a,d in pairs]);n=int(mask.sum());graph=coo_matrix((np.ones(2*len(aa)),(np.r_[aa,dd],np.r_[dd,aa])),shape=(n,n)).tocsr();count,labels=connected_components(graph,directed=False)
# Width of the widest continuous interior corridor, excluding terminal spreading regions.
from scipy.ndimage import distance_transform_edt,label as image_label
clearance=distance_transform_edt(mask)*step;terminal=np.zeros(mask.shape,bool)
for x,y in source_xy+load_xy:terminal|=((xx-x)**2+(yy-y)**2)<1.5**2

def terminal_labels(labels,pts):
 ans=set()
 for x,y in pts:
  patch=((xx-x)**2+(yy-y)**2)<.35**2;ans.update(np.unique(labels[patch&mask]).tolist())
 ans.discard(0);return ans
lo=0.;hi=5.
for _ in range(10):
 mid=(lo+hi)/2;lab,_=image_label(mask&((clearance>=mid)|terminal))
 if terminal_labels(lab,source_xy)&terminal_labels(lab,load_xy):lo=mid
 else:hi=mid
corridor_width_mm=2*lo
source=np.zeros(mask.shape,dtype=bool);load=np.zeros_like(source)
for role,pts,radius,target in [('source',source_xy,config.get('source_radius_mm',.3),source),('load',load_xy,config.get('load_radius_mm',.3),load)]:
 for x,y in pts:
  contact=((xx-x)**2+(yy-y)**2)<radius**2
  if not np.any(contact&mask): raise ValueError(f'{role} terminal ({x},{y}) has no raster contact at selected grid')
  target|=contact
source=ids[source&mask];load=ids[load&mask];
if np.any(source<0) or np.any(load<0): raise ValueError('terminal has no raster contact at selected grid')
source_labels=set(labels[source].tolist()); load_labels=set(labels[load].tolist()); common=source_labels & load_labels
if not common: raise ValueError('rasterized main island has no source-load path at this resolution')
label=max(common,key=lambda lab:sum(labels==lab))
if not source_labels <= {label} or not load_labels <= {label}: raise ValueError('terminal set spans disconnected raster components; refusing to drop isolated terminals')
keep=labels==label;graph=graph[keep][:,keep];orig=np.flatnonzero(keep);remap=np.full(n,-1,np.int32);remap[orig]=np.arange(len(orig));source=remap[source[labels[source]==label]];load=remap[load[labels[load]==label]];degree=np.asarray(graph.sum(axis=1)).ravel();L=diags(degree)-graph;free=np.ones(len(orig),bool);free[source]=False;L=L[free][:,free].tocsr();rhs=np.zeros(len(orig));rhs[load]=1/len(load);rhs=rhs[free];M=diags(1/L.diagonal());start=time.monotonic();sol=spsolve(L,rhs);info=0;volts=np.zeros(len(orig));volts[free]=sol;R_squares=float(np.mean(volts[load]));rho=1.724e-8*(1+.00393*(50-20));result={'board_sha256':__import__('hashlib').sha256(src.read_bytes()).hexdigest(),'configuration':config,'method':'2D four-neighbour resistive sheet on the largest filled main-rail polygon; excludes parallel copper and vias, so estimates only this plane contribution. Not a thermal or AC model. Coarse raster must converge before use.','grid_mm':step,'widest_interior_corridor_mm':corridor_width_mm,'corridor_terminal_exclusion_radius_mm':1.5,'nodes':len(orig),'solver_info':info,'elapsed_s':time.monotonic()-start,'equivalent_squares':R_squares,'residual_l2':float(np.linalg.norm(L@sol-rhs)),'rho_at50C_ohm_m':rho,'resistance_at15um_ohm':R_squares*rho/15e-6,'resistance_at30um_ohm':R_squares*rho/30e-6};out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
