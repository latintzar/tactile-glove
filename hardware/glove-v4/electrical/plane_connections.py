"""Add short, clearance-checked power-to-plane connections. KiCad DRC is authoritative."""

import sys
if "--legacy-six-layer" not in sys.argv:
 raise RuntimeError("Historical six-layer generator. Current eight-layer native candidate and placement.json are authoritative; use current routing helpers. Pass --legacy-six-layer only in an isolated scratch copy.")
from pathlib import Path
from collections import defaultdict,Counter
import pcbnew as k,json,math
from shapely.geometry import Point,LineString,box,Polygon
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
P=Path(__file__).resolve().parent;mm=k.FromMM;xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));v=lambda a:k.VECTOR2I(mm(a[0]),mm(a[1]));layers=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.In3_Cu,k.In4_Cu,k.B_Cu]
b=k.LoadBoard(str(P/'glove-v4-repair.kicad_pcb'))
# Replace the two approximate supply regions by explicit non-overlapping power domains.
for z in list(b.Zones()):
 if not z.GetIsRuleArea() and z.GetNetname()!='GND':b.RemoveNative(z)
regions=[(k.In3_Cu,'3V3_SYS',[(.4,.4),(99.6,.4),(99.6,79.6),(.4,79.6)],0),(k.In3_Cu,'VBAT',[(2,57),(22,57),(22,65.6),(2,65.6)],1),(k.In2_Cu,'3V3_A',[(.4,.4),(89.6,.4),(89.6,66.9),(43,66.9),(43,59.6),(.4,59.6)],0),(k.In2_Cu,'VSYS',[(2,59.9),(42,59.9),(42,76.7),(2,76.7)],1),(k.In2_Cu,'USB_CHARGER_IN',[(90.4,52),(99.6,52),(99.6,79.6),(13,79.6),(13,77.1),(42.4,77.1),(42.4,67.3),(90.4,67.3)],1)]
planes=defaultdict(list)
for layer,net,poly,pri in regions:
 z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet(net));z.SetLocalClearance(mm(.2));z.SetPadConnection(k.ZONE_CONNECTION_FULL);z.SetMinThickness(mm(.15));z.SetAssignedPriority(pri);o=z.Outline();o.NewOutline()
 for p in poly:o.Append(mm(p[0]),mm(p[1]))
 z.SetZoneName(net+' power distribution');b.Add(z);planes[net].append(Polygon(poly))
planes['GND']=[box(.4,.4,99.6,79.6)]
# Discard only identified conflicting widened segments, preserving the valid rest.
for t in list(b.GetTracks()):
 if type(t)==k.PCB_VIA:continue
 if (t.GetNetname()=='VREF_SUPPLY' and math.dist(xy(t.GetStart()),(57.1026,42.658))<.001) or (t.GetNetname()=='BAT_SENSE' and math.dist(xy(t.GetStart()),(58.401,63.9222))<.001):b.RemoveNative(t)
def pg(p):
 x,y=xy(p.GetPosition());w,h=xy(p.GetSize())
 if p.GetShape()==k.PAD_SHAPE_CIRCLE:return Point(x,y).buffer(w/2)
 if p.GetShape()==k.PAD_SHAPE_ROUNDRECT:
  r=k.ToMM(p.GetRoundRectCornerRadius());g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r)
 else:g=box(-w/2,-h/2,w/2,h/2)
 return translate(rotate(g,-p.GetOrientationDegrees(),origin=(0,0)),x,y)
items=[];holes=[];keep=[]
for f in b.GetFootprints():
 for p in f.Pads():
  items.append((pg(p),p.GetNetname(),[l for l in layers if p.IsOnLayer(l)]))
  if p.GetDrillSize().x:holes.append((xy(p.GetPosition()),max(xy(p.GetDrillSize()))))
for t in b.GetTracks():
 via=type(t)==k.PCB_VIA;geom=Point(xy(t.GetPosition())).buffer(k.ToMM(t.GetWidth())/2) if via else LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2)
 items.append((geom,t.GetNetname(),layers if via else [t.GetLayer()]))
 if via:holes.append((xy(t.GetPosition()),k.ToMM(t.GetDrillValue())))
for z in b.Zones():
 if not z.GetIsRuleArea():continue
 o=z.Outline()
 for i in range(o.OutlineCount()):
  q=o.COutline(i);geom=Polygon([xy(q.CPoint(j)) for j in range(q.PointCount())]);ls=[l for l in layers if z.GetLayerSet().Contains(l)];keep.append((geom,ls,z.GetDoNotAllowVias(),z.GetDoNotAllowTracks()))
tree=STRtree([x[0] for x in items]);added=[]
def clear(g,net,ls):
 for i in tree.query(g.buffer(.15002)):
  h,n,ll=items[int(i)]
  if n!=net and set(ll)&set(ls) and g.distance(h)<.15001:return False
 for h,n,ll in added:
  if n!=net and set(ll)&set(ls) and g.distance(h)<.15001:return False
 return True
def via_ok(pt,net):
 if not(.81<pt[0]<99.19 and .81<pt[1]<79.19):return False
 if not any(poly.contains(Point(pt)) for poly in planes[net]):return False
 if net=='3V3_SYS' and box(2,57,22,65.6).contains(Point(pt)):return False
 g=Point(pt).buffer(.3)
 if not clear(g,net,layers):return False
 if any(math.dist(pt,p)<(.3+d)/2+.25001 for p,d in holes):return False
 if any(via and g.intersects(h) for h,ls,via,tr in keep):return False
 return True
def path_ok(a,z,net,l,width):
 g=LineString([a,z]).buffer(width/2)
 return clear(g,net,[l]) and not any(tr and l in ls and g.intersects(h) for h,ls,via,tr in keep)
report=[]
# Largest reservoir lands first, then all remaining plane-net lands.
pads=sorted([(p,f.GetReference()) for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() in planes and not p.GetDrillSize().x],key=lambda q:-q[0].GetSize().x*q[0].GetSize().y)
for p,ref in pads:
 net=p.GetNetname();a=xy(p.GetPosition());l=k.B_Cu if p.IsOnLayer(k.B_Cu) else k.F_Cu
 existing=[xy(t.GetPosition()) for t in b.GetTracks() if type(t)==k.PCB_VIA and t.GetNetname()==net]
 if any(math.dist(a,c)<.75 and path_ok(a,c,net,l,.15) for c in existing):continue
 candidates=[a]
 for radius in [.55,.75,1,1.25,1.5,2,2.5,3]:
  candidates.extend((a[0]+radius*math.cos(i*math.pi/16),a[1]+radius*math.sin(i*math.pi/16)) for i in range(32))
 found=None
 for pt in candidates:
  if not via_ok(pt,net):continue
  width=.25
  if math.dist(a,pt)>1e-6 and not path_ok(a,pt,net,l,width):
   width=.15
   if not path_ok(a,pt,net,l,width):continue
  found=pt;break
 if found is None:continue
 z=k.PCB_VIA(b);z.SetPosition(v(found));z.SetWidth(mm(.6));z.SetDrill(mm(.3));z.SetViaType(k.VIATYPE_THROUGH);z.SetLayerPair(k.F_Cu,k.B_Cu);z.SetNet(b.FindNet(net));b.Add(z);holes.append((found,.3));added.append((Point(found).buffer(.3),net,layers))
 if math.dist(a,found)>1e-6:
  t=k.PCB_TRACK(b);t.SetStart(v(a));t.SetEnd(v(found));t.SetWidth(mm(width));t.SetLayer(l);t.SetNet(b.FindNet(net));b.Add(t);added.append((LineString([a,found]).buffer(width/2),net,[l]))
 report.append({'ref':ref,'pad':p.GetNumber(),'net':net,'via_mm':found})
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'glove-v4-plane.kicad_pcb'),b);(P/'glove-v4-plane.kicad_pro').write_bytes((P/'glove-v4-prepared.kicad_pro').read_bytes());k.WriteDRCReport(b,str(P/'plane-drc.txt'),k.EDA_UNITS_MILLIMETRES,True);(P/'plane-connections.json').write_text(json.dumps(report,indent=2)+'\n');print('Added',len(report),Counter(r['net'] for r in report),flush=True)
