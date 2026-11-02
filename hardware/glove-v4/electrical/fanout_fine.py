"""Escape isolated fine-pitch pins before local routing; preserve high-current copper."""
from pathlib import Path
import pcbnew as k,json,re,math,sys
from shapely.geometry import Point,LineString,Polygon,box
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
P=Path(__file__).resolve().parent;src=Path(sys.argv[1]);dst=Path(sys.argv[2]);b=k.LoadBoard(str(src));__import__("routing_layers").assert_stack(b);mm=k.FromMM;xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));v=lambda p:k.VECTOR2I(mm(p[0]),mm(p[1]));layers=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.In3_Cu,k.In4_Cu,k.In5_Cu,k.In6_Cu,k.B_Cu]
def pg(p):
 if p.GetShape()==k.PAD_SHAPE_CUSTOM:
  q=p.GetBoundingBox();return box(k.ToMM(q.GetLeft()),k.ToMM(q.GetTop()),k.ToMM(q.GetRight()),k.ToMM(q.GetBottom()))
 x,y=xy(p.GetPosition());w,h=xy(p.GetSize())
 if p.GetShape()==k.PAD_SHAPE_CIRCLE:return Point(x,y).buffer(w/2)
 if p.GetShape()==k.PAD_SHAPE_ROUNDRECT:
  r=k.ToMM(p.GetRoundRectCornerRadius());g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r)
 else:g=box(-w/2,-h/2,w/2,h/2)
 return translate(rotate(g,-p.GetOrientationDegrees(),origin=(0,0)),x,y)
b.GetDesignSettings().m_ViasMinSize=mm(.4)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.WriteDRCReport(b,str(P/'fanout-before.drc.txt'),k.EDA_UNITS_MILLIMETRES,True);s=(P/'fanout-before.drc.txt').read_text();targets=set()
for block in s.split('\n['):
 if block.startswith('unconnected_items]'):targets.update(re.findall(r'Pad (\S+) \[.+?\] of (\S+) on',block))
fps={f.GetReference():f for f in b.GetFootprints()};pads=[(p,pg(p)) for f in b.GetFootprints() for p in f.Pads() if any(p.IsOnLayer(l) for l in layers)];ptree=STRtree([g for p,g in pads]);ti=[]
for t in b.GetTracks():
 via=type(t)==k.PCB_VIA;g=(Point(xy(t.GetPosition())) if via else LineString([xy(t.GetStart()),xy(t.GetEnd())])).buffer(k.ToMM(t.GetWidth())/2);ti.append((t,g,via))
ttree=STRtree([g for t,g,vi in ti]);alive={t.m_Uuid.AsString() for t,g,vi in ti};added=[];keep=[];report=[]
for z in b.Zones():
 if not z.GetIsRuleArea():continue
 o=z.Outline()
 for i in range(o.OutlineCount()):
  q=o.COutline(i);keep.append((Polygon([xy(q.CPoint(j)) for j in range(q.PointCount())]),[l for l in layers if z.GetLayerSet().Contains(l)],z.GetDoNotAllowVias(),z.GetDoNotAllowTracks()))
protected_vias=[(29,65),(30.3,67.2),(31.1,67.2),(14.75,69.9),(8.815,67.6),(8.815,68.4)]+[(x,y) for x in [15.35,16.65] for y in [66.35,67.65]]
def trial(a,q,net,l,mid=None):
 if not(.85<q[0]<99.15 and .85<q[1]<79.15):return None
 vg=Point(q).buffer(.2);tg=LineString([a,mid,q] if mid else [a,q]).buffer(.075);g=vg.union(tg)
 for i in ptree.query(g.buffer(.5)):
  p,h=pads[int(i)]
  if p.GetAttribute()==k.PAD_ATTRIB_NPTH:
   hole=Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2)
   if g.distance(hole)<.249999:return None
  if p.GetDrillSize().x and math.dist(q,xy(p.GetPosition()))<(.2+max(xy(p.GetDrillSize())))/2+.25001:return None
  if p.GetNetname()!=net and (vg.distance(h)<.149999 or (p.IsOnLayer(l) and tg.distance(h)<.149999)):return None
 for h,ls,vi,tr in keep:
  if (vi and vg.intersects(h)) or (tr and l in ls and tg.intersects(h)):return None
 removed=[]
 for i in ttree.query(g.buffer(.3)):
  t,h,via=ti[int(i)]
  if t.m_Uuid.AsString() not in alive:continue
  if t.GetNetname()==net:
   if via and math.dist(q,xy(t.GetPosition()))<(.2+k.ToMM(t.GetDrillValue()))/2+.25001:return None
   continue
  if vg.distance(h)<.149999 or ((via or t.GetLayer()==l) and tg.distance(h)<.149999):
   if (not via and t.GetWidth()>=mm(.25)) or (via and (t.GetNetname() in ['GND','VSYS','VBAT','VBAT_ENTRY','USB_CHARGER_IN','USB_VBUS','3V3_SYS','3V3_A','VREF_SUPPLY'] or any(math.dist(xy(t.GetPosition()),p)<.01 for p in protected_vias))):return None
   removed.append((t,via))
 for h,n,ll in added:
  if n==net and len(ll)==8 and vg.distance(h)<.00001:return None
  if n!=net and (vg.distance(h)<.149999 or (l in ll and tg.distance(h)<.149999)):return None
 return removed
for pin,ref in sorted(targets,key=lambda x:(x[1]!='J14',x[1],int(x[0]) if x[0].isdigit() else 999)):
 if not(ref.startswith(('U','R','C','SW')) or ref=='J14'):continue
 f=fps[ref];pp=[p for p in f.Pads() if p.GetNumber()==pin]
 if not pp:continue
 p=pp[0];net=p.GetNetname()
 if not net or net in ['VSYS','USB_CHARGER_IN','VBAT']:continue
 if list(b.GetConnectivity().GetConnectedTracks(p)):continue
 a=xy(p.GetPosition());fc=xy(f.GetPosition());bb=p.GetBoundingBox();horizontal=bb.GetWidth()>bb.GetHeight();direction=(1 if a[0]>=fc[0] else -1,0) if horizontal else (0,1 if a[1]>=fc[1] else -1);l=k.B_Cu if f.IsFlipped() else k.F_Cu;best=None
 for dist in [0,.65,.85,1.1,1.35,1.6,2,2.5,3,4,5,-.65,-.85,-1.1,-1.35,-1.6,-2,-2.5,-3,-4,-5]:
  for offset in [0,.15,-.15,.3,-.3]:
   q=(a[0]+direction[0]*dist-direction[1]*offset,a[1]+direction[1]*dist+direction[0]*offset);rm=trial(a,q,net,l)
   if rm is None:continue
   score=sum(2 if vi else 1 for t,vi in rm)*3+abs(dist)+abs(offset)
   if best is None or score<best[0]:best=(score,q,rm,[a,q])
 if best is None or best[0]>9:
  for ed in [.85,1.15,-.85,-1.15]:
   mid=(a[0]+direction[0]*ed,a[1]+direction[1]*ed)
   for dx in [-2,-1.5,-1,-.5,0,.5,1,1.5,2]:
    for dy in [-2,-1.5,-1,-.5,0,.5,1,1.5,2]:
     if dx==dy==0:continue
     q=(mid[0]+dx,mid[1]+dy);rm=trial(a,q,net,l,mid)
     if rm is None:continue
     score=sum(2 if vi else 1 for t,vi in rm)*3+abs(ed)+math.hypot(dx,dy)
     if best is None or score<best[0]:best=(score,q,rm,[a,mid,q])
 if best is None:continue
 score,q,rm,path=best
 if score>18:continue
 for t,vi in rm:alive.discard(t.m_Uuid.AsString());b.RemoveNative(t)
 for aa,qq in zip(path,path[1:]):
  if math.dist(aa,qq)<1e-6:continue
  t=k.PCB_TRACK(b);t.SetStart(v(aa));t.SetEnd(v(qq));t.SetWidth(mm(.15));t.SetLayer(l);t.SetNet(b.FindNet(net));b.Add(t)
 added.append((LineString(path).buffer(.075),net,[l]))
 z=k.PCB_VIA(b);z.SetPosition(v(q));z.SetWidth(mm(.4));z.SetDrill(mm(.2));z.SetViaType(k.VIATYPE_THROUGH);z.SetLayerPair(k.F_Cu,k.B_Cu);z.SetNet(b.FindNet(net));b.Add(z);added.append((Point(q).buffer(.2),net,layers));report.append({'ref':ref,'pin':pin,'net':net,'via_mm':q,'displaced_items':len(rm)});print(report[-1],flush=True)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());b.SetFileName(str(dst));k.SaveBoard(str(dst),b);proj=json.loads(src.with_suffix('.kicad_pro').read_text());proj['board']['design_settings']['rules']['min_via_diameter']=.4;dst.with_suffix('.kicad_pro').write_text(json.dumps(proj,indent=2)+'\n');k.WriteDRCReport(b,str(dst.with_suffix('.drc.txt')),k.EDA_UNITS_MILLIMETRES,True);dst.with_suffix('.fanout.json').write_text(json.dumps(report,indent=2)+'\n');print('Fanout added',len(report),flush=True)
