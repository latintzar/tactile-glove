"""Native-board USB path, reference-plane and first-order impedance audit.
Uses TI SLVA531A section 7.1 equations; this is not a field-solver or USB eye test.
"""
from pathlib import Path
import pcbnew as k,sys,json,math,hashlib,heapq,itertools
from shapely.geometry import Point,LineString,Polygon,box
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
src=Path(sys.argv[1]);out=Path(sys.argv[2]);b=k.LoadBoard(str(src));xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));names={'USB_DP','USB_DM','MCU_USB_DP','MCU_USB_DM'};graph={};pads={};ts=[t for t in b.GetTracks() if t.GetNetname() in names];nodes={}
def node(n,l,p):return (n,l,round(p[0],6),round(p[1],6))
def edge(a,d,w):graph.setdefault(a,[]).append((d,w));graph.setdefault(d,[]).append((a,w))
for t in ts:
 n=t.GetNetname()
 if t.Type()==k.PCB_VIA_T:
  p=xy(t.GetPosition());edge(node(n,k.F_Cu,p),node(n,k.B_Cu,p),1.6)
 else:
  a,d=xy(t.GetStart()),xy(t.GetEnd());edge(node(n,t.GetLayer(),a),node(n,t.GetLayer(),d),math.dist(a,d))
for f in b.GetFootprints():
 for p in f.Pads():
  n=p.GetNetname()
  if n not in names:continue
  pos=xy(p.GetPosition());w,h=xy(p.GetSize());g=translate(rotate(box(-w/2,-h/2,w/2,h/2),-p.GetOrientationDegrees(),origin=(0,0)),*pos)
  for l in [k.F_Cu,k.B_Cu]:
   if not p.IsOnLayer(l):continue
   key=node(n,l,pos);pads[f.GetReference(),p.GetNumber()]=key
   for other in list(graph):
    if other[:2]==(n,l) and g.buffer(.001).covers(Point(other[2:])):edge(key,other,math.dist(pos,other[2:]))
for ref in ['R202','R203']:
 a,d=pads[ref,'1'],pads[ref,'2'];edge(a,d,math.dist(a[2:],d[2:]))
def shortest(a,d):
 queue=[(0,a)];dist={a:0}
 while queue:
  v,n=heapq.heappop(queue)
  if v!=dist[n]:continue
  if n==d:return v
  for nxt,w in graph.get(n,[]):
   if v+w<dist.get(nxt,1e99):dist[nxt]=v+w;heapq.heappush(queue,(v+w,nxt))
 raise ValueError(('No routed path',a,d))
paths={}
for orient,dp,dm in [('A','A6','A7'),('B','B6','B7')]:
 a=shortest(pads['J11',dp],pads['U51','14']);d=shortest(pads['J11',dm],pads['U51','13']);paths[orient]={'DP_geometric_length_mm':a,'DM_geometric_length_mm':d,'mismatch_mm':abs(a-d)}
# Main coupled body, including one dielectric height of lateral reference margin.
ground=[]
for z in b.Zones():
 if z.GetIsRuleArea() or z.GetNetname()!='GND' or z.GetLayer()!=k.In6_Cu:continue
 q=z.GetFilledPolysList(z.GetLayer())
 for i in range(q.OutlineCount()):
  o=q.COutline(i);holes=[]
  for h in range(q.HoleCount(i)):
   p=q.CHole(i,h);holes.append([xy(p.CPoint(j)) for j in range(p.PointCount())])
  ground.append(Polygon([xy(o.CPoint(j)) for j in range(o.PointCount())],holes))
ground=unary_union(ground);corridor=box(94.25-.075-.092,55,94.65+.075+.092,61);uncovered=corridor.difference(ground)
# Confirm main coupled segments are present exactly in the native board.
main=[]
for n,x in [('USB_DP',94.65),('USB_DM',94.25)]:
 found=[t for t in ts if t.Type()!=k.PCB_VIA_T and t.GetNetname()==n and t.GetLayer()==k.B_Cu and abs(xy(t.GetStart())[0]-x)<.0001 and abs(xy(t.GetEnd())[0]-x)<.0001 and min(xy(t.GetStart())[1],xy(t.GetEnd())[1])<=55.0001 and max(xy(t.GetStart())[1],xy(t.GetEnd())[1])>=60.9999 and abs(k.ToMM(t.GetWidth())-.15)<.0001];assert len(found)==1,(n,found);main.append(found[0].m_Uuid.AsString())
gv=[xy(t.GetPosition()) for t in b.GetTracks() if t.Type()==k.PCB_VIA_T and t.GetNetname()=='GND'];transitions=[]
for t in ts:
 if t.Type()!=k.PCB_VIA_T:continue
 p=xy(t.GetPosition());nearest=sorted((math.dist(p,q),q) for q in gv)[:2];transitions.append({'net':t.GetNetname(),'xy_mm':p,'nearest_two_ground_vias':[{'distance_mm':d,'xy_mm':q} for d,q in nearest]})
# Verify every routed surface segment against its adjacent GND, excluding only
# 0.5 mm local antipad neighbourhoods at the USB signal transitions.
planes={}
for layer in [k.In1_Cu,k.In6_Cu]:
 gg=[]
 for z in b.Zones():
  if z.GetIsRuleArea() or z.GetNetname()!='GND' or z.GetLayer()!=layer:continue
  q=z.GetFilledPolysList(layer)
  for i in range(q.OutlineCount()):
   a=q.COutline(i);holes=[]
   for h in range(q.HoleCount(i)):
    c=q.CHole(i,h);holes.append([xy(c.CPoint(j)) for j in range(c.PointCount())])
   gg.append(Polygon([xy(a.CPoint(j)) for j in range(a.PointCount())],holes))
 planes[layer]=unary_union(gg)
antipads=unary_union([Point(xy(t.GetPosition())).buffer(.5) for t in ts if t.Type()==k.PCB_VIA_T]);reference_segments=[]
for t in ts:
 if t.Type()==k.PCB_VIA_T:continue
 layer=k.In1_Cu if t.GetLayer()==k.F_Cu else k.In6_Cu
 shape=LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2).difference(antipads);gap=shape.difference(planes[layer])
 reference_segments.append({'net':t.GetNetname(),'layer':b.GetLayerName(t.GetLayer()),'uuid':t.m_Uuid.AsString(),'uncovered_area_mm2':gap.area,'uncovered_bbox_mm':list(gap.bounds) if not gap.is_empty else None})
def impedance(w=.15,s=.25,h=.092,t=.035,er=4.1):
 z0=87/math.sqrt(er+1.41)*math.log(5.98*h/(.8*w+t));return 2*z0*(1-.48*math.exp(-.96*s/h))
# Screening corners are assumed process variation, not a supplier tolerance guarantee.
corners=[impedance(w,s,h,t,er) for w in [.14,.16] for s in [.24,.26] for h in [.0874,.0966] for t in [.028,.040] for er in [3.9,4.3]]
result={'board_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'status':'engineering_geometry_audit','path_lengths':paths,'path_method':'Shortest copper-centerline graph from each connector orientation to module USB pad centers, including 1.6 mm per traversed full-board via and equal 1.65 mm resistor pad-center distance. Pad-internal paths use Euclidean center-to-endpoint distances. Not extracted electrical delay.','series_resistor_to_module_tracks_mm':{n:sum(k.ToMM(t.GetLength()) for t in ts if t.Type()!=k.PCB_VIA_T and t.GetNetname()==n) for n in ['MCU_USB_DP','MCU_USB_DM']},'main_pair':{'signal_layer':'B.Cu','reference_layer':'In6 GND_BOTTOM','width_mm':.15,'edge_gap_mm':.25,'parallel_body_length_mm':6,'track_uuids':main,'reference_corridor_bbox_mm':list(corridor.bounds),'reference_uncovered_area_mm2':uncovered.area,'continuous_reference_under_coupled_body':uncovered.area<1e-8},'transitions':transitions,'surface_reference_check':{'excluded_usb_via_antipad_radius_mm':.5,'segments':reference_segments,'total_uncovered_area_mm2':sum(x['uncovered_area_mm2'] for x in reference_segments)},'first_order_microstrip_estimate':{'equation_source':'https://www.ti.com/lit/an/slva531a/slva531a.pdf#page=15','stackup':'JLC081611-3313','w_mm':.15,'s_mm':.25,'h_mm':.092,'copper_mm':.035,'er':4.1,'nominal_differential_ohm':impedance(),'target_ohm':90,'target_tolerance_percent':10,'assumed_corner_range_ohm':[min(corners),max(corners)],'corner_assumptions':{'width_mm':[.14,.16],'gap_mm':[.24,.26],'dielectric_mm':[.0874,.0966],'copper_mm':[.028,.040],'er':[3.9,4.3]}},'layout_source':'https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html#usb','limitations':['Solder mask, trapezoidal etch, pads, ESD package, resistor discontinuities and via parasitics are not included in the closed-form estimate.','Connector and ESD fanouts are uncoupled local discontinuities; six millimetres is the constant-gap body, not a claim of uniform impedance over every pad.','The supplier must confirm 90 ohm +/-10% using its actual stack, controlled-impedance process and coupon; this calculation is a nominal geometry target.','USB eye/compliance, powered enumeration and radiated immunity require fabricated hardware.']}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'paths':paths,'reference_uncovered_mm2':uncovered.area,'impedance':result['first_order_microstrip_estimate']},indent=2))
