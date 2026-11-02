from pathlib import Path
import pcbnew as k,sys,json,math,hashlib,collections,re
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
bpath=Path(sys.argv[1]);out=Path(sys.argv[2]);b=k.LoadBoard(str(bpath));xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));vias=[t for t in b.GetTracks() if t.Type()==k.PCB_VIA_T];tracks=[t for t in b.GetTracks() if t.Type()!=k.PCB_VIA_T];gn=[xy(t.GetPosition()) for t in vias if t.GetNetname()=='GND'];outnets={}
for n in ['USB_DP','USB_DM','MCU_USB_DP','MCU_USB_DM']:
 ts=[t for t in tracks if t.GetNetname()==n];vs=[t for t in vias if t.GetNetname()==n];other=n.replace('DP','DM') if 'DP' in n else n.replace('DM','DP');peer={l:unary_union([LineString([xy(t.GetStart()),xy(t.GetEnd())]) for t in tracks if t.GetNetname()==other and t.GetLayer()==l]) for l in [k.F_Cu,k.In2_Cu,k.In5_Cu,k.B_Cu]};close=0;total=0
 for t in ts:
  a,d=xy(t.GetStart()),xy(t.GetEnd());length=math.dist(a,d);N=max(1,math.ceil(length/.2));g=peer[t.GetLayer()]
  for i in range(N):
   q=Point(a[0]+(d[0]-a[0])*(i+.5)/N,a[1]+(d[1]-a[1])*(i+.5)/N);total+=length/N
   if not g.is_empty and q.distance(g)<=.35:close+=length/N
 outnets[n]={'total_routed_segment_length_mm':sum(k.ToMM(t.GetLength()) for t in ts),'segment_count':len(ts),'via_count':len(vs),'layers':dict(collections.Counter(b.GetLayerName(t.GetLayer()) for t in ts)),'widths_mm':sorted(set(round(k.ToMM(t.GetWidth()),6) for t in ts)),'length_fraction_with_other_member_centerline_within_0p35mm_same_layer':close/total if total else None,'pads':[{'ref':f.GetReference(),'pin':p.GetNumber(),'xy_mm':xy(p.GetPosition())} for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()==n]}
fast=[]
for t in vias:
 n=t.GetNetname()
 if n not in outnets and not re.match(r'^(MCU_)?CAM_(D[0-7]|PCLK|XCLK|HREF|VSYNC)$',n):continue
 q=xy(t.GetPosition());d=min(math.dist(q,a) for a in gn);fast.append({'net':n,'xy_mm':q,'nearest_ground_via_distance_mm':d})
result={'board_sha256':hashlib.sha256(bpath.read_bytes()).hexdigest(),'USB_geometry':outnets,'fast_signal_vias':fast,'nearest_ground_via_target_mm':2,'fast_vias_exceeding_target':[v for v in fast if v['nearest_ground_via_distance_mm']>2],'limitations':['Segment sums include branches and stubs and are not end-to-end propagation length.','Nearness metric alone does not prove differential impedance, return continuity or coupling.','Ground-via distance is an engineering screening target and is not a device-specific timing limit.','Controlled USB routing review remains a release gate.']};out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'USB':outnets,'fast_vias':len(fast),'over_2mm':len(result['fast_vias_exceeding_target']),'max_ground_via_distance_mm':max(v['nearest_ground_via_distance_mm'] for v in fast)},indent=2))
