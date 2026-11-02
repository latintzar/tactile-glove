#!/usr/bin/env python3
from pathlib import Path
import sys,json,re,hashlib
import pcbnew as k
P=Path(__file__).resolve().parent;O=P/'hand-tile';sys.path.insert(0,str(P.parents[1]/'glove-v3/electrical'))
from import_ses import import_session
b=k.LoadBoard(str(O/'hand-tile-unrouted.kicad_pcb'));stats=import_session(b,O/'hand-tile.ses')

mm=k.FromMM
ground=b.FindNet('GND')
# Continuous return beneath I2C, with ordinary vias outside solder lands.
for x,y in [(4.5,3.006),(6.288,4.7),(13.775,6.5)]:
 via=k.PCB_VIA(b);via.SetPosition(k.VECTOR2I(mm(x),mm(y)));via.SetWidth(mm(.6));via.SetDrill(mm(.3));via.SetViaType(k.VIATYPE_THROUGH);via.SetLayerPair(k.F_Cu,k.B_Cu);via.SetNet(ground);b.Add(via)
z=k.ZONE(b);z.SetLayer(k.B_Cu);z.SetNet(ground);z.SetLocalClearance(mm(.15));z.SetMinThickness(mm(.15));z.SetPadConnection(k.ZONE_CONNECTION_FULL)
outline=z.Outline();outline.NewOutline()
for x,y in [(1.2,.4),(14.8,.4),(15.6,1.2),(15.6,14.8),(14.8,15.6),(1.2,15.6),(.4,14.8),(.4,1.2)]:outline.Append(mm(x),mm(y))
b.Add(z);k.ZONE_FILLER(b).Fill(b.Zones())

# Native connectivity and clearance check, independently from autorouter status.
b.SetFileName(str(O/'hand-tile-routed.kicad_pcb'));b.BuildConnectivity();k.SaveBoard(str(O/'hand-tile-routed.kicad_pcb'),b)
assert k.WriteDRCReport(b,str(O/'hand-tile-drc.txt'),k.EDA_UNITS_MILLIMETRES,True)
t=(O/'hand-tile-drc.txt').read_text();counts={n:int(v) for v,n in re.findall(r'Found (\d+) (DRC violations|unconnected pads|Footprint errors)',t)}
actual={(f.GetReference(),p.GetNumber()):p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode()}
d=json.loads((O/'parts.json').read_text());expected={(d['reference_map'][p['ref']],pin):net for p in d['parts'] for pin,net in p['pins'].items() if net!='NC'};expected[('J1','MP')]='GND'
assert actual==expected, {'extra':list(set(actual.items())-set(expected.items())),'missing':list(set(expected.items())-set(actual.items()))}
report={'board':'hand-tile-routed.kicad_pcb','parts':len(d['parts']),'size_mm':[16,16,.8],'counts':counts,'native_endpoints_reconciled':True,'connected_endpoints':len(expected),'routing':{**stats,'ground_stitch_vias':3,'total_vias':3},'board_sha256':hashlib.sha256((O/'hand-tile-routed.kicad_pcb').read_bytes()).hexdigest()}
report['ground_plane']='Continuous B.Cu ground with three 0.3mm drilled stitching vias; ordinary vias outside solder lands.'
(O/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));print(t[:1800])

assert all(v == 0 for v in counts.values()), counts
