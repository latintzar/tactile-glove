import pcbnew as k, json, sys
from shapely.geometry import Polygon,Point,box,LineString
from shapely.ops import nearest_points
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP,Circle
b=k.LoadBoard(sys.argv[1]);xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));pt=Point(13.875,68.45);roi=box(10,64,20,73)
fig,ax=plt.subplots(figsize=(10,9))
for z in b.Zones():
 if z.GetLayer()!=3 or z.GetIsRuleArea():continue
 q=z.GetFilledPolysList(z.GetLayer());geoms=[]
 for i in range(q.OutlineCount()):
  o=q.COutline(i);holes=[]
  for h in range(q.HoleCount(i)):
   a=q.CHole(i,h);holes.append([xy(a.CPoint(j)) for j in range(a.PointCount())])
  g=Polygon([xy(o.CPoint(j)) for j in range(o.PointCount())],holes);geoms.append(g)
  c=g.intersection(roi)
  if c.is_empty:continue
  col='#eb764f' if z.GetNetname()=='USB_CHARGER_IN' else '#c8d8e1'
  for a in ([c] if c.geom_type=='Polygon' else c.geoms):
   if a.geom_type!='Polygon':continue
   ax.add_patch(MP(a.exterior.coords,color=col,alpha=.7))
   for h in a.interiors:ax.add_patch(MP(h.coords,color='white'))
 if z.GetNetname()=='USB_CHARGER_IN':
  g=min(geoms,key=pt.distance);print('plane distance',g.distance(pt),'nearest',nearest_points(g,pt)[0]);print('zone polygon coordinates', [xy(z.Outline().COutline(0).CPoint(j)) for j in range(z.Outline().COutline(0).PointCount())])
for t in b.GetTracks():
 via=type(t)==k.PCB_VIA
 if not via and t.GetLayer()!=3:continue
 p=xy(t.GetStart());e=xy(t.GetEnd());g=Point(p).buffer(k.ToMM(t.GetWidth())/2) if via else LineString([p,e]).buffer(k.ToMM(t.GetWidth())/2)
 if not g.intersects(roi):continue
 ax.add_patch(MP(g.exterior.coords,color='red' if t.GetNetname()=='USB_CHARGER_IN' else '#607080'))
 if via:
  ax.add_patch(Circle(p,k.ToMM(t.GetDrillValue())/2,color='white'))
  ax.text(*p,t.GetNetname(),fontsize=6)
ax.plot(13.875,68.45,'kx');ax.set_xlim(10,20);ax.set_ylim(73,64);ax.set_aspect('equal');ax.grid(alpha=.2);fig.savefig(sys.argv[2],dpi=100)
