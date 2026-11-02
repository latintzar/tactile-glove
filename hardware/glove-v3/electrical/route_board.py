"""Bounded Specctra preparation/import, plane fill and actual KiCad DRC."""
from pathlib import Path
import argparse,json,re,hashlib
import pcbnew as k
P=Path(__file__).parent
ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','import','check']);ap.add_argument('--runtime',default='/tmp/glove-eda-runtime');ap.add_argument('--session',default='grouped.ses');args=ap.parse_args();T=Path(args.runtime)
if args.action=='prepare':
 pro=json.loads((P/'glove-v3-floorplan.kicad_pro').read_text())
 for cls in pro['net_settings']['classes']:
  cls.update({'clearance':.15,'track_width':.15,'via_diameter':.6,'via_drill':.3})
 pro['board']['design_settings']['rules'].update({'min_clearance':.15,'min_track_width':.15,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_hole_to_hole':.25})
 for name in ('glove-v3-grouped','glove-v3-routed'):(P/(name+'.kicad_pro')).write_text(json.dumps(pro,indent=2))
 b=k.LoadBoard(str(P/'glove-v3-grouped.kicad_pcb'))
 d=b.GetDesignSettings().m_NetSettings.m_DefaultNetClass;d.SetClearance(k.FromMM(.15));d.SetTrackWidth(k.FromMM(.15));d.SetViaDiameter(k.FromMM(.6));d.SetViaDrill(k.FromMM(.3))
 assert k.ExportSpecctraDSN(b,str(T/'grouped.dsn'))
 s=(T/'grouped.dsn').read_text()
 # Keep layers active: FreeRouting must be able to terminate vias on the plane polygons.
 # Prevent telemetry and bound both route and optimization in the invocation.
 (T/'grouped.dsn').write_text(s)
 print('Exported',T/'grouped.dsn')
else:
 b=k.LoadBoard(str(P/('glove-v3-grouped.kicad_pcb' if args.action=='import' else 'glove-v3-routed.kicad_pcb')))
 if args.action=='import':
  from import_ses import import_session
  print(import_session(b,T/args.session))
 # Reconcile exact current canonical MPNs without moving footprints or changing nets.
 parts=json.loads((P/'components.json').read_text())['components'];refmap=json.loads((P/'reference-map.json').read_text());mpns={refmap[p['ref']]:p['mpn'] for p in parts}
 expected={(refmap[p['ref']],pin):net for p in parts for pin,net in p['pins'].items() if net!='NC'}
 actual={(f.GetReference(),pad.GetNumber()):pad.GetNetname() for f in b.GetFootprints() for pad in f.Pads() if pad.GetNetCode()!=0}
 assert actual==expected, {'missing':list(set(expected.items())-set(actual.items())),'extra':list(set(actual.items())-set(expected.items()))}
 assert set(mpns)=={f.GetReference() for f in b.GetFootprints()}
 for f in b.GetFootprints():
  f.SetValue(mpns[f.GetReference()])
  if f.GetReference()==refmap['J_XIAO']:
   for g in f.GraphicalItems():
    if g.GetLayer()==k.F_SilkS:g.SetLayer(k.F_Fab)
 k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity()
 b.SetFileName(str(P/'glove-v3-routed.kicad_pcb'));k.SaveBoard(str(P/'glove-v3-routed.kicad_pcb'),b)
 assert k.WriteDRCReport(b,str(P/'glove-v3-routed-drc.txt'),k.EDA_UNITS_MILLIMETRES,True)
 text=(P/'glove-v3-routed-drc.txt').read_text();counts={name:int(count) for count,name in re.findall(r'Found (\d+) (DRC violations|unconnected pads|Footprint errors)',text)};print(text[:1500])
 report={'board':'glove-v3-routed.kicad_pcb','tracks':sum(type(t)==k.PCB_TRACK for t in b.GetTracks()),'vias':sum(type(t)==k.PCB_VIA for t in b.GetTracks()),'counts':counts,'canonical_sha256':hashlib.sha256((P/'components.json').read_bytes()).hexdigest(),'board_sha256':hashlib.sha256((P/'glove-v3-routed.kicad_pcb').read_bytes()).hexdigest(),'canonical_endpoint_count':len(expected),'endpoint_reconciliation_pass':actual==expected,'drc_pass':not re.search(r'Severity: error',text)}
 (P/'routing-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
