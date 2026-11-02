"""Route the converter high-current switching paths explicitly; report any displaced copper."""
from pathlib import Path
import pcbnew as k,json,math,sys
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
P=Path(__file__).resolve().parent;src=Path(sys.argv[1]);dst=Path(sys.argv[2]);b=k.LoadBoard(str(src));mm=k.FromMM;xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));v=lambda p:k.VECTOR2I(mm(p[0]),mm(p[1]));log=[]
def pg(p):
 if p.GetShape()==k.PAD_SHAPE_CUSTOM:
  q=p.GetBoundingBox();return box(k.ToMM(q.GetLeft()),k.ToMM(q.GetTop()),k.ToMM(q.GetRight()),k.ToMM(q.GetBottom()))
 x,y=xy(p.GetPosition());w,h=xy(p.GetSize())
 if p.GetShape()==k.PAD_SHAPE_CIRCLE:return Point(x,y).buffer(w/2)
 if p.GetShape()==k.PAD_SHAPE_ROUNDRECT:
  r=k.ToMM(p.GetRoundRectCornerRadius());g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r)
 else:g=box(-w/2,-h/2,w/2,h/2)
 return translate(rotate(g,-p.GetOrientationDegrees(),origin=(0,0)),x,y)
def clear_for(g,net,layer,via=False):
 for f in b.GetFootprints():
  for p in f.Pads():
   if p.GetNetname()==net or not(via or p.IsOnLayer(layer)):continue
   assert g.distance(pg(p))>=.14999,(net,'pad collision',f.GetReference(),p.GetNumber(),g.distance(pg(p)))
 for t in list(b.GetTracks()):
  isvia=type(t)==k.PCB_VIA
  if t.GetNetname()==net or not(via or isvia or t.GetLayer()==layer):continue
  q=Point(xy(t.GetPosition())).buffer(k.ToMM(t.GetWidth())/2) if isvia else LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2)
  if g.distance(q)<.15:log.append({'displaced_net':t.GetNetname(),'type':'via' if isvia else 'track','start_mm':xy(t.GetPosition())});b.RemoveNative(t)
def path(net,pts,width):
 g=LineString(pts).buffer(width/2);clear_for(g,net,k.F_Cu)
 for a,z in zip(pts,pts[1:]):
  t=k.PCB_TRACK(b);t.SetStart(v(a));t.SetEnd(v(z));t.SetWidth(mm(width));t.SetLayer(k.F_Cu);t.SetNet(b.FindNet(net));b.Add(t)
 log.append({'power_path':net,'points_mm':pts,'width_mm':width})
# Low-inductance converter input and output connections to the local capacitors.
path('VSYS',[(29.775,63.6),(29.275,63.6),(29.275,62.8)],.25)
path('VSYS',[(29.275,62.8),(28.225,62.8),(28.225,62.0)],.4)
path('3V3_SYS',[(29.275,66.4),(29.275,67.2)],.25)
path('3V3_SYS',[(29.775,66.4),(29.775,67.2),(29.275,67.2)],.25)
path('3V3_SYS',[(29.275,67.2),(30.3,67.2)],.25)
path('3V3_SYS',[(30.3,67.2),(31.225,68.5)],.6)
path('USB_CHARGER_IN',[(14.75,68.975),(14.75,69.9)],.28)
path('USB_CHARGER_IN',[(14.025,68.25),(13.6,68.25),(13.6,69.9),(14.75,69.9)],.28)
for net,pt in [('3V3_SYS',(30.3,67.2)),('3V3_SYS',(31.1,67.2)),('USB_CHARGER_IN',(14.75,69.9))]:
 clear_for(Point(pt).buffer(.3),net,k.F_Cu,True)
 for t in list(b.GetTracks()):
  if type(t)==k.PCB_VIA and math.dist(xy(t.GetPosition()),pt)<(k.ToMM(t.GetDrillValue())+.3)/2+.25:b.RemoveNative(t)
 z=k.PCB_VIA(b);z.SetPosition(v(pt));z.SetWidth(mm(.6));z.SetDrill(mm(.3));z.SetViaType(k.VIATYPE_THROUGH);z.SetLayerPair(k.F_Cu,k.B_Cu);z.SetNet(b.FindNet(net));b.Add(z)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());b.SetFileName(str(dst));k.SaveBoard(str(dst),b);dst.with_suffix('.kicad_pro').write_bytes(src.with_suffix('.kicad_pro').read_bytes());k.WriteDRCReport(b,str(dst.with_suffix('.drc.txt')),k.EDA_UNITS_MILLIMETRES,True);dst.with_suffix('.power.json').write_text(json.dumps(log,indent=2)+'\n');print(log,flush=True)
