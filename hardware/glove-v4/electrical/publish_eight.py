"""Publish a net-reconciled eight-layer engineering checkpoint and physical placement."""
from pathlib import Path
import pcbnew as k,json,hashlib,os,collections,datetime,sys,math
E=Path(sys.argv[2]);src=Path(sys.argv[1]);b=k.LoadBoard(str(src));parts=json.loads((E/'components.json').read_text())['components'];fps={f.GetReference():f for f in b.GetFootprints()};assert len(fps)==len(parts)
errors=[]
for c in parts:
 f=fps[c['designator']]
 for p in f.Pads():
  n=p.GetNumber()
  if n not in c['pins']:continue
  want=c['pins'][n];want='' if want=='NC' else want
  if p.GetNetname()!=want:errors.append([c['designator'],n,want,p.GetNetname()])
assert not errors,errors
s=src.with_suffix('.drc.txt').read_text();counts=dict(collections.Counter(x.split(']')[0] for x in s.split('\n[')[1:]));physical=sum('Severity: error' in x for x in s.split('\n[')[1:] if not x.startswith('unconnected_items]'));assert physical==0
files={'glove-v4-routing-candidate.kicad_pcb':src.read_bytes(),'glove-v4-routing-candidate.kicad_pro':src.with_suffix('.kicad_pro').read_bytes(),'routing-candidate.drc.txt':s.replace(str(src),'glove-v4-routing-candidate.kicad_pcb').encode()}
sha=hashlib.sha256(files['glove-v4-routing-candidate.kicad_pcb']).hexdigest();csha=hashlib.sha256((E/'components.json').read_bytes()).hexdigest()
status=json.loads((E/'routing-progress.json').read_text());status.update(component_count=len(parts),copper_layers=8,unconnected_items=counts.get('unconnected_items',0),physical_drc_errors=0,report_counts=counts,candidate_sha256=sha,components_sha256=csha,canonical_pad_net_mismatches=0,verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),current_process='Local pin escapes and USB differential-pair layout correction',manufacturing_ready=False,stackup_template='JLC081611-3313',nominal_finished_thickness_mm=1.6,template_compressed_thickness_mm=1.636)
status['release_blockers']=['Remaining electrically open nets','USB differential-pair rerouting and reference-plane audit','Final camera/ADC timing and return-path geometry review','Fabricator stackup, copper/plating and VIPPO confirmation'];
d=json.loads((E/'placement.json').read_text());old={x['ref']:x for x in d['parts']};new=[]
for c in parts:
 f=fps[c['designator']];f.BuildCourtyardCaches();q=f.GetCourtyard(k.B_CrtYd if f.IsFlipped() else k.F_CrtYd);bb=q.BBox();x=dict(old.get(c['ref'],{}));x.update(ref=c['ref'],designator=c['designator'],x_mm=k.ToMM(f.GetPosition().x),y_mm=k.ToMM(f.GetPosition().y),rotation_deg=f.GetOrientationDegrees(),side='B' if f.IsFlipped() else 'F',courtyard_mm=[k.ToMM(bb.GetX()),k.ToMM(bb.GetY()),k.ToMM(bb.GetRight()),k.ToMM(bb.GetBottom())],subsystem=c['subsystem'],footprint=c['footprint'])
 if old.get(c['ref'],{}).get('body_bbox_mm'):
  before=old[c['ref']]; ox,oy=before['x_mm'],before['y_mm']; oa=math.radians(before['rotation_deg']); na=math.radians(x['rotation_deg']); bx=before['body_bbox_mm']; corners=[]
  for px,py in [(bx[0],bx[1]),(bx[0],bx[3]),(bx[2],bx[1]),(bx[2],bx[3])]:
   dx,dy=px-ox,py-oy; lx=dx*math.cos(oa)-dy*math.sin(oa);ly=dx*math.sin(oa)+dy*math.cos(oa)
   if before['side']!=x['side']:ly=-ly
   corners.append((x['x_mm']+lx*math.cos(na)+ly*math.sin(na),x['y_mm']-lx*math.sin(na)+ly*math.cos(na)))
  x['body_bbox_mm']=[round(min(p[0] for p in corners),6),round(min(p[1] for p in corners),6),round(max(p[0] for p in corners),6),round(max(p[1] for p in corners),6)]
 if c['ref']=='J_BAT':x.update(body_bbox_mm=[.525,65.26,7.675,75.17],manufacturer_bare_header_height_max_mm=9.27,assembly_height_allowance_mm=.20,manufacturer_mated_height_status="Mechanical conservative envelope11.26mm; exact wire exit pending STEP",mating_direction=[0,1],pin1_xy_mm=[4.1,66.25],pin2_xy_mm=[4.1,63.25],locating_hole_xy_mm=[4.1,70.57],locating_hole_diameter_mm=3.0,mated_housing_envelope_status='Pending mechanical verification against Molex housing drawing')
 if c['ref']=='J_BAT':x.pop('manufacturer_mated_height_mm',None)
 if c['ref']=='F_BAT':x.update(body_bbox_mm=[8.85,73.53,15.15,76.47],manufacturer_max_body_height_mm=2.94,body_height_source='Littelfuse 451/453 datasheet dimensions 2.69 +/-0.25 mm')
 if c['ref']=='L_CHARGER':x['body_bbox_mm']=[8.5,65.8,12.9,70.2]
 new.append(x)
d.update(parts=new,component_count=len(new),copper_layers=8,circuit_sha256=csha,board_sha256=sha,stackup_function=['F signal','In1 continuous GND','In2 signal','In3 power','In4 power','In5 signal','In6 continuous GND','B signal'],status='Actual routed engineering checkpoint; routing incomplete',power_layout_note='Two dedicated inner power layers, two continuous ground layers. Power integrity audit and remaining-net closure are required before fabrication.')
d['ports']['battery']={'ref':'J_BAT','mating_direction':[0,1],'mouth_y_mm':75.17,'locating_peg_to_rear_edge_mm':9.43,'manufacturer_peg_to_edge_max_mm':10.16,'housing_mpn':'43025-0200','contacts_mpn':'43030-0007','wire_awg':22,'mated_service_envelope_status':'Mechanical drawing verification pending'}
files['routing-progress.json']=(json.dumps(status,indent=2)+'\n').encode();files['placement.json']=(json.dumps(d,indent=2)+'\n').encode();files['publish_eight.py']=Path(__file__).read_bytes()
for name,data in files.items():
 dst=E/name;tmp=dst.with_name(dst.name+'.tmp');tmp.write_bytes(data);os.chown(tmp,1003,1003);os.replace(tmp,dst)
print(json.dumps(status,indent=2))
