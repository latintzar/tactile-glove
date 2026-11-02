from pathlib import Path
import pcbnew as k,json,hashlib,collections,re,math
from shapely.geometry import Point,box
from shapely.affinity import rotate,translate
P=Path('/tmp/glove-eda-runtime/power-cad-fix');SRC=next(a for a in Path(__file__).resolve().parents if (a / 'hardware/glove-v4').is_dir()) / 'hardware/glove-v3/electrical';parts=json.loads((SRC/'components.json').read_text())['components'];refs=json.loads((SRC/'reference-map.json').read_text());rev={v:z for z,v in refs.items()};by={refs[c['ref']]:c for c in parts};b=k.LoadBoard(str(P/'local.kicad_pcb'));old=k.LoadBoard(str(SRC/'glove-v3-routed.kicad_pcb'));xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));oldvias={xy(t.GetPosition()) for t in old.GetTracks() if type(t)==k.PCB_VIA}
expected={(refs[c['ref']],pin):net for c in parts for pin,net in c['pins'].items() if net!='NC'};actual={(f.GetReference(),p.GetNumber()):p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode()!=0};assert expected==actual;assert set(by)=={f.GetReference() for f in b.GetFootprints()}
extra=[];via_in_pad=[];vias=[t for t in b.GetTracks() if type(t)==k.PCB_VIA];via_shapes={t.m_Uuid.AsString():Point(xy(t.GetPosition())).buffer(k.ToMM(t.GetDrillValue())/2) for t in vias}
for f in b.GetFootprints():
 c=by[f.GetReference()];f.SetValue(c['mpn'])
 for pad in f.Pads():
  if pad.GetNumber() not in ['', 'MP'] and pad.GetNumber() not in c['pins']:extra.append((f.GetReference(),pad.GetNumber(),pad.GetNetname()))
  if pad.GetAttribute()!=k.PAD_ATTRIB_SMD:continue
  x,y=xy(pad.GetPosition());w,h=xy(pad.GetSize());r=k.ToMM(pad.GetRoundRectCornerRadius()) if pad.GetShape()==k.PAD_SHAPE_ROUNDRECT else 0
  g=box(-w/2+r,-h/2+r,w/2-r,h/2-r).buffer(r) if r else box(-w/2,-h/2,w/2,h/2);g=translate(rotate(g,-pad.GetOrientationDegrees(),origin=(0,0)),x,y).buffer(.05)
  for t in vias:
   q=xy(t.GetPosition())
   if via_shapes[t.m_Uuid.AsString()].intersects(g):via_in_pad.append({'ref':f.GetReference(),'pad':pad.GetNumber(),'via_mm':q,'existing_before_correction':q in oldvias})
assert not extra,extra
k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();b.SetFileName(str(P/'glove-v3-routed.kicad_pcb'));k.SaveBoard(str(P/'glove-v3-routed.kicad_pcb'),b);k.WriteDRCReport(b,str(P/'glove-v3-routed-drc.txt'),k.EDA_UNITS_MILLIMETRES,True);s=(P/'glove-v3-routed-drc.txt').read_text();counts={name:int(n) for n,name in re.findall(r'Found (\d+) (DRC violations|unconnected pads|Footprint errors)',s)}
r={'board':'glove-v3-routed.kicad_pcb','revision':'V3.3 tactile core; camera/12h power architecture separate','tracks':sum(type(t)==k.PCB_TRACK for t in b.GetTracks()),'vias':sum(type(t)==k.PCB_VIA for t in b.GetTracks()),'counts':counts,'canonical_sha256':hashlib.sha256((SRC/'components.json').read_bytes()).hexdigest(),'board_sha256':hashlib.sha256((P/'glove-v3-routed.kicad_pcb').read_bytes()).hexdigest(),'canonical_endpoint_count':len(expected),'component_count':len(parts),'endpoint_reconciliation_pass':True,'all_numbered_footprint_pads_declared':not extra,'drc_pass':all(v==0 for v in counts.values()),'via_drill_overlap_with_smd_mask':via_in_pad};(P/'routing-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
checks=json.loads((SRC/'pcb-engineering-checks.json').read_text());checks.update(board_sha256=r['board_sha256'],component_count=len(parts),distinct_connected_nets=len({n for n in actual.values()}),track_segments_by_layer=dict(collections.Counter(b.GetLayerName(t.GetLayer()) for t in b.GetTracks() if type(t)==k.PCB_TRACK)),routing_method='Preserved original four-layer routes; V3.3 reference/buffer/20-clamp additions completed by clearance-conservative local routing and escape vias; orphan stubs removed; all native pads reconciled; zones refilled and KiCad DRC run with unchanged rules.')
for key,prefix in [('charge_input_nets','CHG_IN_'),('adc_nets','ADC_'),('bias_nets','V')]:
 checks[key]={net:{'total_branch_length_mm':round(sum(k.ToMM(t.GetLength()) for t in b.GetTracks() if type(t)==k.PCB_TRACK and t.GetNetname()==net),4),'vias':sum(type(t)==k.PCB_VIA and t.GetNetname()==net for t in b.GetTracks())} for net in sorted({n for n in actual.values() if n.startswith(prefix)})}
(P/'pcb-engineering-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
