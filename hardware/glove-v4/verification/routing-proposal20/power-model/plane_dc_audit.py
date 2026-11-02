"""Conservative 2D resistive-sheet approximation of the main filled power island."""
import pcbnew as k,sys,json,time
from pathlib import Path
import numpy as np,shapely
from shapely.geometry import Polygon
from scipy.sparse import coo_matrix,diags
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve
src=Path(sys.argv[1]);out=Path(sys.argv[2]);step=float(sys.argv[3]) if len(sys.argv)>3 else .1;config=json.loads(Path(sys.argv[4]).read_text()) if len(sys.argv)>4 else {};b=k.LoadBoard(str(src));xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));gs=[]
for z in b.Zones():
 if z.GetIsRuleArea() or z.GetNetname()!=config.get('net','3V3_SYS') or (config.get('layer') and b.GetLayerName(z.GetLayer())!=config['layer']):continue
 q=z.GetFilledPolysList(z.GetLayer())
 for i in range(q.OutlineCount()):
  o=q.COutline(i);holes=[]
  for h in range(q.HoleCount(i)):
   a=q.CHole(i,h);holes.append([xy(a.CPoint(j)) for j in range(a.PointCount())])
  gs.append(Polygon([xy(o.CPoint(j)) for j in range(o.PointCount())],holes))
g=max(gs,key=lambda p:p.area);xs=np.arange(.5,99.5,step);ys=np.arange(.5,79.5,step);xx,yy=np.meshgrid(xs,ys);mask=shapely.contains_xy(g,xx,yy);ids=np.full(mask.shape,-1,dtype=np.int32);ids[mask]=np.arange(mask.sum());pairs=[]
for a,d in [(ids[:,:-1],ids[:,1:]),(ids[:-1,:],ids[1:,:])]:
 good=(a>=0)&(d>=0);pairs.append((a[good],d[good]))
aa=np.concatenate([a for a,d in pairs]);dd=np.concatenate([d for a,d in pairs]);n=int(mask.sum());graph=coo_matrix((np.ones(2*len(aa)),(np.r_[aa,dd],np.r_[dd,aa])),shape=(n,n)).tocsr();count,labels=connected_components(graph,directed=False)
# Width of the widest continuous interior corridor, excluding terminal spreading regions.
from scipy.ndimage import distance_transform_edt,label as image_label
clearance=distance_transform_edt(mask)*step;terminal=np.zeros(mask.shape,bool)
for x,y in config.get('sources',[(30.3,67.2),(31.1,67.2)])+config.get('loads',[(98.5,77.24),(97.2879,77.5467)]):terminal|=((xx-x)**2+(yy-y)**2)<1.5**2
source_xy=config.get('sources',[(30.3,67.2),(31.1,67.2)]);load_xy=config.get('loads',[(98.5,77.24),(97.2879,77.5467)])
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
for x,y in config.get('sources',[(30.3,67.2),(31.1,67.2)]):source|=((xx-x)**2+(yy-y)**2)<config.get('source_radius_mm',.3)**2
for x,y in config.get('loads',[(98.5,77.24),(97.2879,77.5467)]):load|=((xx-x)**2+(yy-y)**2)<config.get('load_radius_mm',.3)**2
source=ids[source&mask];load=ids[load&mask];common=set(labels[source])&set(labels[load]);assert common,'Rasterized main island has no source-load path at this resolution';label=max(common,key=lambda lab:sum(labels==lab));keep=labels==label;graph=graph[keep][:,keep];orig=np.flatnonzero(keep);remap=np.full(n,-1,np.int32);remap[orig]=np.arange(len(orig));source=remap[source[labels[source]==label]];load=remap[load[labels[load]==label]];degree=np.asarray(graph.sum(axis=1)).ravel();L=diags(degree)-graph;free=np.ones(len(orig),bool);free[source]=False;L=L[free][:,free].tocsr();rhs=np.zeros(len(orig));rhs[load]=1/len(load);rhs=rhs[free];M=diags(1/L.diagonal());start=time.monotonic();sol=spsolve(L,rhs);info=0;volts=np.zeros(len(orig));volts[free]=sol;R_squares=float(np.mean(volts[load]));rho=1.724e-8*(1+.00393*(50-20));result={'board_sha256':__import__('hashlib').sha256(src.read_bytes()).hexdigest(),'configuration':config,'method':'2D four-neighbour resistive sheet on the largest filled main-rail polygon; excludes parallel copper and vias, so estimates only this plane contribution. Not a thermal or AC model. Coarse raster must converge before use.','grid_mm':step,'widest_interior_corridor_mm':corridor_width_mm,'corridor_terminal_exclusion_radius_mm':1.5,'nodes':len(orig),'solver_info':info,'elapsed_s':time.monotonic()-start,'equivalent_squares':R_squares,'residual_l2':float(np.linalg.norm(L@sol-rhs)),'rho_at50C_ohm_m':rho,'resistance_at15um_ohm':R_squares*rho/15e-6,'resistance_at30um_ohm':R_squares*rho/30e-6};out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
