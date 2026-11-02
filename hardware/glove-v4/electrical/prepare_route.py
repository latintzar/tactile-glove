from pathlib import Path

import sys
if "--legacy-six-layer" not in sys.argv:
 raise RuntimeError("Historical six-layer generator. Current eight-layer native candidate and placement.json are authoritative; use current routing helpers. Pass --legacy-six-layer only in an isolated scratch copy.")
import pcbnew as k,json,math,sys,hashlib
from shapely.geometry import Point,LineString,box,Polygon
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
P=Path(__file__).resolve().parent;R=next(a for a in Path(__file__).resolve().parents if (a / 'hardware/glove-v4').is_dir()) / 'hardware';E=R/'glove-v4/electrical'
mm=k.FromMM;xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));v=lambda x,y:k.VECTOR2I(mm(x),mm(y));layers=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.In3_Cu,k.In4_Cu,k.B_Cu]
pro=json.loads((R/'glove-v3/electrical/glove-v3-routed.kicad_pro').read_text());pro['meta']['filename']='glove-v4-prepared.kicad_pro';pro['board']['design_settings']['rules']['min_through_hole_diameter']=0.2
for name in ['glove-v4-placement','glove-v4-prepared','glove-v4-routed']:(P/(name+'.kicad_pro')).write_text(json.dumps(pro,indent=2)+'\n')
refs=json.loads((E/'reference-map.json').read_text());parts={p['ref']:p for p in json.loads((E/'components.json').read_text())['components']};logical={n:r for r,n in refs.items()}
# Scoped manufacturer thermal-pad hole exception, with 0.30mm router vias unchanged.
for name in ['glove-v4-placement','glove-v4-prepared','glove-v4-routed']:(P/(name+'.kicad_dru')).write_text('(version 1)\n(rule "ESP32 manufacturer thermal holes" (condition "A.memberOfFootprint(\''+refs['U_MCU']+'\')") (constraint hole_size (min 0.2mm)))\n')
b=k.LoadBoard(str(P/'glove-v4-placement.kicad_pcb'));fps={logical[f.GetReference()]:f for f in b.GetFootprints()}
# The catalog hatched regions are copied from the source footprint drawing into enforceable F.Cu areas.
f=fps['J_SD'];cx,cy=xy(f.GetPosition())
sdregions=[[-7.225,-7.275,-6.475,-4.025],[-7.225,-2.825,-6.475,.775],[-6.125,-1.425,-5.425,6.175],[-5.425,-2.725,3.275,-1.125],[2.925,6.975,5.475,8.325]]
for i,(x0,y0,x1,y1) in enumerate(sdregions):
 z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(k.F_Cu);z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowCopperPour(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetZoneName('Hirose DM3AT catalog no conductive traces '+str(i));o=z.Outline();o.NewOutline()
 for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:o.Append(mm(cx+x),mm(cy+y))
 b.Add(z)
def pg(p):
 x,y=xy(p.GetPosition());w,h=xy(p.GetSize())
 if p.GetShape()==k.PAD_SHAPE_CIRCLE:return Point(x,y).buffer(w/2)
 if p.GetShape()==k.PAD_SHAPE_ROUNDRECT:
  r=k.ToMM(p.GetRoundRectCornerRadius());g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r)
 else:g=box(-w/2,-h/2,w/2,h/2)
 return translate(rotate(g,-p.GetOrientationDegrees(),origin=(0,0)),x,y)
newpads=[]
for r,f in fps.items():
 for p in f.Pads():newpads.append((p,pg(p),r))
tree=STRtree([x[1] for x in newpads]);shapeindex={id(x[1]):x for x in newpads}
removed=[]
for t in list(b.GetTracks()):
 via=type(t)==k.PCB_VIA;g=Point(xy(t.GetPosition())) if via else LineString([xy(t.GetStart()),xy(t.GetEnd())]);rad=k.ToMM(t.GetWidth())/2
 for shape in tree.query(g.buffer(rad+.7)):
  p,shape,pr=newpads[int(shape)]
  if not via and not p.IsOnLayer(t.GetLayer()):continue
  if p.GetNetname()!=t.GetNetname() and g.distance(shape)<rad+.14999:
   removed.append({'net':t.GetNetname(),'uuid':str(t.m_Uuid),'near':pr});b.RemoveNative(t);break
  if via and p.GetDrillSize().x and math.dist(xy(t.GetPosition()),xy(p.GetPosition()))<k.ToMM(t.GetDrillValue()+p.GetDrillSize().x)/2+.251:
   removed.append({'net':t.GetNetname(),'uuid':str(t.m_Uuid),'near':'drill'});b.RemoveNative(t);break
# Filled/capped BQ thermal vias, 0.30mm drill, 0.60mm copper. Their stencil remains segmented.
f=fps['U_CHARGER'];cx,cy=xy(f.GetPosition())
for dx in [-.65,.65]:
 for dy in [-.65,.65]:
  z=k.PCB_VIA(b);z.SetPosition(v(cx+dx,cy+dy));z.SetWidth(mm(.6));z.SetDrill(mm(.3));z.SetViaType(k.VIATYPE_THROUGH);z.SetLayerPair(k.F_Cu,k.B_Cu);z.SetNet(b.FindNet('GND'));b.Add(z)
# Manufacturer source is intentionally preserved; hide decorative silkscreen under dense components.
for f in b.GetFootprints():
 for g in f.GraphicalItems():
  if g.GetLayer() in [k.F_SilkS,k.B_SilkS]:g.SetLayer(k.F_Fab if g.GetLayer()==k.F_SilkS else k.B_Fab)
d=b.GetDesignSettings().m_NetSettings.m_DefaultNetClass;d.SetClearance(mm(.15));d.SetTrackWidth(mm(.15));d.SetViaDiameter(mm(.6));d.SetViaDrill(mm(.3))
b.BuildConnectivity();b.SetFileName(str(P/'glove-v4-prepared.kicad_pcb'));k.SaveBoard(b.GetFileName(),b)
# Source footprint table resolves library comparisons without changing physical copper.
(P/'fp-lib-table').write_text('(fp_lib_table (lib (name GloveV4)(type KiCad)(uri "${KIPRJMOD}/footprints")(options "")(descr "Pinned manufacturer and KiCad lands")))\n')
assert k.ExportSpecctraDSN(b,str(P/'glove-v4.dsn'))
s=(P/'glove-v4.dsn').read_text()
for layer in ['In1.Cu','In4.Cu']:s=s.replace('(layer '+layer+'\n      (type signal)','(layer '+layer+'\n      (type power)')
(P/'glove-v4.dsn').write_text(s)
(P/'preparation.json').write_text(json.dumps({'removed_conflicting_retained_items':removed,'remaining_track_items':len(list(b.GetTracks())),'sd_source':'Hirose DM3 series catalog p3 manufacturer hatched no-trace areas','sd_keepout_local_mm':sdregions},indent=2)+'\n')
print('Removed',len(removed),'items; exported DSN',flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.WriteDRCReport(b,str(P/'prepared-drc.txt'),k.EDA_UNITS_MILLIMETRES,True)
print('DRC written',flush=True)
