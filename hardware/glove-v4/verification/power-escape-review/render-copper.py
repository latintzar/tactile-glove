import sys,pcbnew as k,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Circle
from shapely.geometry import box
import pcbnew as k,json,math
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
b=k.LoadBoard(sys.argv[1])
xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y))
def pg(p):
 x,y=xy(p.GetPosition());w,h=xy(p.GetSize());a=-p.GetOrientationDegrees()
 if p.GetShape()==k.PAD_SHAPE_CIRCLE:return Point(x,y).buffer(w/2)
 if p.GetShape()==k.PAD_SHAPE_ROUNDRECT:
  r=k.ToMM(p.GetRoundRectCornerRadius());q=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r)
 else:q=box(-w/2,-h/2,w/2,h/2)
 return translate(rotate(q,a,origin=(0,0)),x,y)

if len(sys.argv)>1:b=k.LoadBoard(sys.argv[1])
fig,axs=plt.subplots(1,2,figsize=(14,7))
for ax,name,bounds in zip(axs,['U32: pin6 output','U42: pin24 power input'],[(84,54,90,60),(11.5,66.5,16,71)]):
 roi=box(*bounds)
 for t in b.GetTracks():
  via=type(t)==k.PCB_VIA
  if not via and t.GetLayer() not in [0,2,5,31]:continue
  a=xy(t.GetStart());c=xy(t.GetEnd());geom=Point(a) if via else LineString([a,c])
  if not geom.intersects(roi):continue
  col='#df5b37' if t.GetNetname()=='USB_CHARGER_IN' else ('#308d85' if t.GetLayer()==31 else '#b5bdc2')
  if via:
   ax.add_patch(Circle(a,k.ToMM(t.GetWidth())/2,facecolor=col,edgecolor='#334',lw=.5,zorder=4));ax.add_patch(Circle(a,k.ToMM(t.GetDrillValue())/2,color='white',zorder=5))
  else:
   g=geom.buffer(k.ToMM(t.GetWidth())/2);ax.add_patch(Polygon(list(g.exterior.coords),facecolor=col,alpha=.65,zorder=1))
 for f in b.GetFootprints():
  for p in f.Pads():
   if not(p.IsOnLayer(0) or p.IsOnLayer(31)):continue
   g=pg(p)
   if not g.intersects(roi):continue
   col='#df5b37' if p.GetNetname()=='USB_CHARGER_IN' else ('#308d85' if p.IsOnLayer(31) else '#7b8a93')
   ax.add_patch(Polygon(list(g.exterior.coords),facecolor=col,alpha=.65,edgecolor='white',lw=.5,zorder=2))
   x,y=xy(p.GetPosition());ax.text(x,y,f.GetReference()+'.'+p.GetNumber(),ha='center',va='center',fontsize=6,zorder=6)
 ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[3],bounds[1]);ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title(name);ax.set_xlabel('Board X (mm)');ax.set_ylabel('Board Y (mm)')
fig.suptitle('Actual KiCad copper: orange = charger input net; teal = backside neighbours',fontsize=13)
fig.tight_layout();fig.savefig(sys.argv[2],dpi=140)
