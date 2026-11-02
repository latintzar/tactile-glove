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
# All switching-node current stays on front copper, with short package necks.
for t in list(b.GetTracks()):
 if t.GetNetname() in ['MAIN_L1','MAIN_L2']:b.RemoveNative(t)
path('MAIN_L1',[(29.775,64.5),(31.0,64.5)],.25)
path('MAIN_L1',[(31.0,64.5),(31.45,63.815),(33.5,63.815)],.8)
path('MAIN_L2',[(29.775,65.5),(31.0,65.5)],.25)
path('MAIN_L2',[(31.0,65.5),(31.45,66.185),(33.5,66.185)],.8)
# Rotate the inductor's symmetric two-terminal package so SW faces the charger.
f=next(f for f in b.GetFootprints() if f.GetReference()=='L1');f.SetOrientationDegrees(180)
for t in list(b.GetTracks()):
 if t.GetNetname()=='CHG_SW':b.RemoveNative(t)
pad=next(p for p in f.Pads() if p.GetNumber()=='1');clear_for(pg(pad),'CHG_SW',k.F_Cu)
path('CHG_SW',[(14.025,65.75),(13.2,65.75)],.28)
path('CHG_SW',[(14.025,66.25),(13.2,66.25),(13.2,65.75)],.28)
path('CHG_SW',[(13.2,65.75),(11.185,65.75),(11.185,68.0)],.8)
# The other inductor terminal enters the broad VSYS plane through two vias.
for pt in [(8.815,67.6),(8.815,68.4)]:
 clear_for(Point(pt).buffer(.3),'VSYS',k.F_Cu,True)
 for t in list(b.GetTracks()):
  if type(t)==k.PCB_VIA and math.dist(xy(t.GetPosition()),pt)<(k.ToMM(t.GetDrillValue())+.3)/2+.25:b.RemoveNative(t)
 z=k.PCB_VIA(b);z.SetPosition(v(pt));z.SetWidth(mm(.6));z.SetDrill(mm(.3));z.SetViaType(k.VIATYPE_THROUGH);z.SetLayerPair(k.F_Cu,k.B_Cu);z.SetNet(b.FindNet('VSYS'));b.Add(z)
# Package PGND accepts a standard 0.45/0.20mm via beside its narrow switch terminals.
pt=(29.0,65.0);clear_for(Point(pt).buffer(.225),'GND',k.F_Cu,True)
for t in list(b.GetTracks()):
 if type(t)==k.PCB_VIA and math.dist(xy(t.GetPosition()),pt)<(k.ToMM(t.GetDrillValue())+.2)/2+.25:log.append({'replaced_nearby_via':t.GetNetname(),'position':xy(t.GetPosition())});b.RemoveNative(t)
z=k.PCB_VIA(b);z.SetPosition(v(pt));z.SetWidth(mm(.45));z.SetDrill(mm(.2));z.SetViaType(k.VIATYPE_THROUGH);z.SetLayerPair(k.F_Cu,k.B_Cu);z.SetNet(b.FindNet('GND'));b.Add(z)
path('GND',[(29.0,65),(29.6,65)],.25)
# Extend the protected USB plane up to the charger's input pins, with priority over VSYS.
for z in b.Zones():
 if not z.GetIsRuleArea() and z.GetNetname()=='USB_CHARGER_IN':
  o=z.Outline();o.RemoveAllContours();o.NewOutline()
  for x,y in [(90.4,52),(99.6,52),(99.6,79.6),(13,79.6),(13,68.8),(15.6,68.8),(15.6,77.1),(42.4,77.1),(42.4,67.3),(90.4,67.3)]:o.Append(mm(x),mm(y))
  z.SetAssignedPriority(2)
pro=json.loads(src.with_suffix('.kicad_pro').read_text());pro['board']['design_settings']['rules']['min_via_diameter']=.45;pro['board']['design_settings']['rules']['min_through_hole_diameter']=.2;dst.with_suffix('.kicad_pro').write_text(json.dumps(pro,indent=2)+'\n');b.GetDesignSettings().m_ViasMinSize=mm(.45);b.GetDesignSettings().m_MinThroughDrill=mm(.2)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());b.SetFileName(str(dst));k.SaveBoard(str(dst),b);k.WriteDRCReport(b,str(dst.with_suffix('.drc.txt')),k.EDA_UNITS_MILLIMETRES,True);dst.with_suffix('.power.json').write_text(json.dumps(log,indent=2)+'\n');print(log,flush=True)
