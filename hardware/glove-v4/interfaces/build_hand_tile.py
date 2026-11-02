#!/usr/bin/env python3
"""Create the actual 16mm hand IMU tile; source pin maps remain authoritative."""
from pathlib import Path
import json,sys,hashlib
import pcbnew as k
P=Path(__file__).resolve().parent;O=P/'hand-tile';O.mkdir(exist_ok=True)
d=json.loads((P/'imu-interface.json').read_text());parts=[p for p in d['parts'] if p['assembly']=='hand-tile']
mm=k.FromMM;v=lambda x,y:k.VECTOR2I(mm(x),mm(y));b=k.BOARD();b.SetCopperLayerCount(2);b.GetDesignSettings().SetBoardThickness(mm(.8))
netnames=sorted({n for p in parts for n in p['pins'].values() if n!='NC'});nets={}
for i,n in enumerate(netnames,1):nets[n]=k.NETINFO_ITEM(b,n,i);b.Add(nets[n])
positions={'U_IMU_HAND':(8,3,0),'C_IMU_HAND_VDD':(11.25,3.75,0),'C_IMU_HAND_IO':(7.5,6,270),'C_IMU_HAND_BULK':(13,7.5,0),'J_IMU_HAND':(8,12,0),'R_IMU_HAND_SDA':(3.5,4.5,270),'R_IMU_HAND_SCL':(11.8,5.5,0)}
refs={'U_IMU_HAND':'U1','C_IMU_HAND_VDD':'C1','C_IMU_HAND_IO':'C2','C_IMU_HAND_BULK':'C3','J_IMU_HAND':'J1','R_IMU_HAND_SDA':'R1','R_IMU_HAND_SCL':'R2'}
for p in parts:
 f=k.FootprintLoad(str(P/'footprints'),p['footprint'].split(':')[1]);assert f,p['footprint']
 f.SetFPID(k.LIB_ID('GloveV4',p['footprint'].split(':')[1]));f.SetReference(refs[p['ref']]);f.SetValue(p['mpn']);f.Value().SetVisible(False);f.Reference().SetVisible(False)
 for pad in f.Pads():
  n=p['pins'].get(pad.GetNumber(),'GND' if pad.GetNumber()=='MP' else 'NC')
  if n!='NC':pad.SetNet(nets[n])
 x,y,a=positions[p['ref']];f.SetPosition(v(x,y));f.SetOrientationDegrees(a);b.Add(f)
edge=[(1,0),(15,0),(16,1),(16,15),(15,16),(1,16),(0,15),(0,1)]
for a,z in zip(edge,edge[1:]+edge[:1]):
 t=k.PCB_SHAPE();t.SetShape(k.SHAPE_T_SEGMENT);t.SetStart(v(*a));t.SetEnd(v(*z));t.SetWidth(mm(.05));t.SetLayer(k.Edge_Cuts);b.Add(t)
for text,x,y in [('HAND',8,1),('WRIST',8,15.2)]:
 t=k.PCB_TEXT(b);t.SetText(text);t.SetPosition(v(x,y));t.SetTextSize(v(.8,.8));t.SetTextThickness(mm(.1));t.SetLayer(k.B_SilkS);t.SetMirrored(True);b.Add(t)
# All physical connections, including the repeated connector shield lands, remain numbered.
nd=b.GetDesignSettings().m_NetSettings.m_DefaultNetClass;nd.SetClearance(mm(.15));nd.SetTrackWidth(mm(.15));nd.SetViaDiameter(mm(.6));nd.SetViaDrill(mm(.3))
base=json.loads((P.parents[1]/'glove-v3/electrical/glove-v3-routed.kicad_pro').read_text())
base['board']['design_settings']['rules'].update({'min_clearance':.15,'min_track_width':.15,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_hole_to_hole':.25})
for c in base['net_settings']['classes']:c.update({'clearance':.15,'track_width':.15,'via_diameter':.6,'via_drill':.3})
for name in ['hand-tile-unrouted','hand-tile-routed']:(O/(name+'.kicad_pro')).write_text(json.dumps(base,indent=2)+'\n')
k.SaveBoard(str(O/'hand-tile-unrouted.kicad_pcb'),b)
assert k.ExportSpecctraDSN(b,str(O/'hand-tile.dsn'))
(O/'parts.json').write_text(json.dumps({'parts':parts,'reference_map':refs,'placements':positions,'board_mm':[16,16,.8],'wire_harness':'Adafruit4210 100mm JSTSH4pin'},indent=2)+'\n')
print('Actual hand tile:',len(parts),'parts',len(netnames),'nets,16x16x0.8mm')
