"""Six-layer cuff layout retaining V3.3 tactile coordinates and unchanged routes."""

import sys
if "--legacy-six-layer" not in sys.argv:
 raise RuntimeError("Historical six-layer generator. Current eight-layer native candidate and placement.json are authoritative; use current routing helpers. Pass --legacy-six-layer only in an isolated scratch copy.")
from pathlib import Path
from collections import defaultdict,Counter
import pcbnew as k,json,math,hashlib
P=Path(__file__).resolve().parent;R=next(a for a in Path(__file__).resolve().parents if (a / 'hardware/glove-v4').is_dir()) / 'hardware';E=R/'glove-v4/electrical';O=R/'glove-v3/electrical'
parts=json.loads((E/'components.json').read_text())['components'];refmap=json.loads((E/'reference-map.json').read_text());by={p['ref']:p for p in parts};oldrefs={v:r for r,v in json.loads((O/'reference-map.json').read_text()).items()}
MOVED={'U_CHG5','CDEC_U_CHG5'}|{prefix+ch for prefix in ['RIN_','RFB_','CFB_','D_CLAMP_'] for ch in ['P3','P4','H1','H2']}
W,H=100.,80.;mm=k.FromMM;v=lambda x,y:k.VECTOR2I(mm(x),mm(y));xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y))
b=k.BOARD();b.SetCopperLayerCount(6);ds=b.GetDesignSettings();ds.SetBoardThickness(mm(1.6));ds.m_MinClearance=mm(.15);ds.m_TrackMinWidth=mm(.15);ds.m_ViasMinSize=mm(.6);ds.m_MinThroughDrill=mm(.3);ds.m_ViasMinAnnularWidth=mm(.15);ds.m_HoleToHoleMin=mm(.25)
netnames=sorted({n for p in parts for n in p['pins'].values() if n!='NC'});nets={n:k.NETINFO_ITEM(b,n,i) for i,n in enumerate(netnames,1)}
for n in nets.values():b.Add(n)
old=k.LoadBoard(str(O/'glove-v3-routed.kicad_pcb'));oldfp={oldrefs.get(f.GetReference()):f for f in old.GetFootprints()};fp={};placed={};occ={0:[],1:[]};pads=defaultdict(list)
# PCB cuts are kept rectangular; the ESP antenna is cantilevered beyond y=80.
for a,z in [((0,0),(W,0)),((W,0),(W,H)),((W,H),(0,H)),((0,H),(0,0))]:
 e=k.PCB_SHAPE();e.SetShape(k.SHAPE_T_SEGMENT);e.SetStart(v(*a));e.SetEnd(v(*z));e.SetLayer(k.Edge_Cuts);e.SetWidth(mm(.05));b.Add(e)
def box(f,body=False):
 pts=[]
 for g in f.GraphicalItems():
  if g.GetLayer() in ([k.F_Fab,k.B_Fab] if body else [k.F_CrtYd,k.B_CrtYd]):
   z=g.GetBoundingBox();pts.extend([(k.ToMM(z.GetLeft()),k.ToMM(z.GetTop())),(k.ToMM(z.GetRight()),k.ToMM(z.GetBottom()))])
 if not pts:
  z=f.GetBoundingBox(False,False);pts=[(k.ToMM(z.GetLeft()),k.ToMM(z.GetTop())),(k.ToMM(z.GetRight()),k.ToMM(z.GetBottom()))]
 return [min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)]
def overlaps(a,z):return a[0]<z[2]-1e-5 and a[2]>z[0]+1e-5 and a[1]<z[3]-1e-5 and a[3]>z[1]+1e-5
for p in parts:
 r=p['ref'];f=oldfp[r].Duplicate() if p['subsystem']=='tactile' and r!='D_LDO_REV' else k.FootprintLoad(str(P/'footprints'),p['footprint'].split(':')[1]);assert f,r
 f.SetReference(refmap[r]);f.SetValue(p.get('value',p['mpn']));f.Reference().SetVisible(False);f.Value().SetVisible(False);f.SetFPID(k.LIB_ID('GloveV4',p['footprint'].split(':')[1]));b.Add(f);fp[r]=f
 for pad in f.Pads():
  n=p['pins'].get(pad.GetNumber());pad.SetNet(nets[n] if n and n!='NC' else b.FindNet(0))
  if n and n!='NC':pads[n].append((r,pad))
 if r in MOVED:f.Move(v(8,18))
 if p['subsystem']=='tactile' and r!='D_LDO_REV':
  side=1 if f.GetLayer()==k.B_Cu else 0;z=box(f);occ[side].append((z,r));placed[r]={'side':side,'box':z}
  if any(z.GetAttribute()==k.PAD_ATTRIB_PTH for z in f.Pads()):occ[1-side].append((box(f),r+' TH'))
# Reuse unchanged routes; remove old power routes whose pin domains changed.
rename={'3V3':'3V3_SYS','3V3A':'3V3_A','ADC_MISO':'ADC_SDO','MUX_SRCLK':'MUX_SHIFT_CLK','MUX_SER':'MUX_DATA','MUX_RCLK':'MUX_LATCH'}
kept=0
for t in old.GetTracks():
 n=t.GetNetname();new=rename.get(n,n)
 if new not in nets or n in ['3V3','3V3A','WAKE_IRQ','BTN0','BAT+','USB_5V']:continue
 if any(n==prefix+ch for prefix in ['PVDF_','CHG_OUT_'] for ch in ['P3','P4','H1','H2']):continue
 q=t.Duplicate();q.SetNet(nets[new]);
 if n in {'CHG_IN_'+ch for ch in ['P3','P4','H1','H2']}:q.Move(v(8,18))
 if type(q)!=k.PCB_VIA:q.SetLayer({k.In1_Cu:k.In2_Cu,k.In2_Cu:k.In3_Cu}.get(q.GetLayer(),q.GetLayer()))
 b.Add(q);kept+=1
local={r:([-9.525,-13.475,9.525,13.475] if r=='U_MCU' else box(f)) for r,f in fp.items() if r not in placed}
def rectangle(r,cx,cy,a):
 z=local[r];w=z[2]-z[0];h=z[3]-z[1]
 if a%180:w,h=h,w
 return [cx-w/2-.10,cy-h/2-.10,cx+w/2+.10,cy+h/2+.10]
def legal(z,side,edge=False):
 if z[0]<.4 or z[2]>(W+1 if edge else W-.4) or z[1]<.4 or (not edge and z[3]>H-.4):return False
 return not any(overlaps(z,o) for o,n in occ[side])
def put(r,cx,cy,a=0,side=0,edge=False):
 z=rectangle(r,cx,cy,a)
 if not legal(z,side,edge):return False
 f=fp[r]
 if side:f.Flip(v(0,0),False)
 f.SetOrientationDegrees(a);f.SetPosition(v(cx,cy));actual=box(f,r=='U_MCU');dx=cx-(actual[0]+actual[2])/2;dy=cy-(actual[1]+actual[3])/2;f.Move(v(dx,dy));actual=box(f,r=='U_MCU')
 occ[side].append((z,r));placed[r]={'side':side,'box':actual}
 if any(p.GetAttribute()==k.PAD_ATTRIB_PTH for p in f.Pads()):occ[1-side].append((z,r+' TH'))
 if r in ['U_CHARGER','U_MAIN']:occ[1-side].append(([cx-2.3,cy-2.3,cx+2.3,cy+2.3],r+' thermal-via area'))
 return True
# The radio's antenna portion overhangs the PCB; its entire source rule area remains active.
assert put('U_MCU',89.75,73.25,180,0,True),'MCU'
# These coordinates separate switching power from the ADC and retain compact local loops.
fixed=[('J_USB',95.5,54.3,90,0,True),('J_BAT',5.5,62.5,0,0,False),('J_NTC',32,76,0,0,True),('J_SD',54,71.0,0,0,True),('J_CAM',90,23,180,0,False),('J_IMU_CUFF',81,14,0,0,False),('U_CHARGER',16,67,90,0,False),('L_CHARGER',10,67,0,0,False),('U_MAIN',29,65,0,0,False),('L_MAIN',32.9,65,270,0,False),('U_CAM_DATA',78,60,0,0,False),('U_CAM_CTRL',79.5,44,0,0,False),('U_IO0',65,70,0,1,False),('U_IO1',75,70,0,1,False),('SW_USER',72,76,0,0,False),('D_RGB',66,76,0,0,False)]
# Candidate search is a geometric clearance check with electrical-distance ranking.
def auto(r,targets,side,angles=(0,90),edge=False):
 weighted=[]
 for n in by[r]['pins'].values():
  if n in ['GND','3V3_SYS','3V3_A','VBAT','VSYS','VREF3V0','1V8','VEXC2V5','VMID1V25']:continue
  for rr,pad in pads[n]:
   if rr in placed:weighted.append((xy(pad.GetPosition()),2 if rr in targets else .25))
 for target in targets:
  if isinstance(target,tuple):weighted.append((target,5))
  elif target in placed:
   z=placed[target]['box'];weighted.append((((z[0]+z[2])/2,(z[1]+z[3])/2),5))
 if not weighted:weighted=[((50,68),1)]
 total=sum(w for p,w in weighted);tx=sum(p[0]*w for p,w in weighted)/total;ty=sum(p[1]*w for p,w in weighted)/total
 candidates=[]
 for radius in [5,10,18,32,120]:
  best=None
  for ix in range(max(2,int((tx-radius)*2)),min(int(2*W)-2,int((tx+radius)*2))+1):
   cx=ix/2
   for iy in range(max(2,int((ty-radius)*2)),min(int(2*H)-2,int((ty+radius)*2))+1):
    cy=iy/2
    for a in angles:
     z=rectangle(r,cx,cy,a)
     if not legal(z,side,edge):continue
     score=sum(math.hypot(cx-p[0],cy-p[1])*w for p,w in weighted)
     if best is None or score<best[0]:best=(score,cx,cy,a)
  if best:
   _,cx,cy,a=best;assert put(r,cx,cy,a,side,edge);return
 raise RuntimeError('No position '+r)
for r,cx,cy,a,side,edge in fixed:
 if not put(r,cx,cy,a,side,edge):auto(r,[(cx,cy)],side,(a,),edge)
# Power chips/diodes first; bypass caps follow their real supply pins.
anchors={'U_USB_HIGH':('J_USB',0),'U_USB_RECOVERY':('J_USB',0),'U_CC':('J_USB',1),'U_BAT_WINDOW':('J_NTC',1),'U_BAT_READY':('U_MAIN',1),'U_ANALOG_LDO':('U_LDO',0),'U_IMU_CUFF':('J_CAM',1),'U_CAM_IO':('J_CAM',1),'U_CAM_AV':('J_CAM',1),'U_CAM_DV':('J_CAM',1),'U_CAM_SCCB':('J_CAM',1),'U_CAM_IF_INV':('U_CAM_CTRL',1),'U_SD_POWER':('J_SD',1),'D_LDO_REV':('U_LDO',0)}
for p in parts:
 r=p['ref']
 if r in placed or not r.startswith(('U_','D_','Q_')):continue
 ar,side=anchors.get(r,('U_IO0',1))
 if r.startswith('D_USB'):ar,side='J_USB',0
 if r.startswith(('Q_REF','Q_VREF')):ar,side='U_REF',1
 if r.startswith('Q_CHG'):ar,side='U_BAT_WINDOW',1
 auto(r,[ar],side)
for r in ['R_MAIN_TOP','R_MAIN_BOT','R_CHG_ICHG','R_CHG_ILIM']:
 auto(r,['U_MAIN' if r.startswith('R_MAIN') else 'U_CHARGER'],0)
# Supply networks are placed ahead of signal pulls, including all 1210 reservoirs.
for p in sorted(parts,key=lambda p:0 if p['ref'].startswith('C_MAIN_LOCAL') or p['ref'] in ['C_CHG_BTST','C_CHG_REGN','C_CHG_PMID'] else (1 if p['footprint'].endswith('C_1210_3225Metric') else 2)):
 r=p['ref']
 if r in placed or not r.startswith('C_'):continue
 side=1
 if r.startswith(('C_CHG','C_SYS','C_BAT')):ar='U_CHARGER';side=0 if r not in ['C_BAT_WINDOW','C_BAT_READY','C_BAT_ADC'] else 1
 elif r.startswith('C_MAIN'):ar='U_MAIN';side=0
 elif r.startswith('C_ANALOG'):ar='U_ANALOG_LDO';side=0
 elif r.startswith('C_REF'):ar='U_REF'
 elif r.startswith('C_CAM'):ar='J_CAM'
 elif r.startswith('C_SD'):ar='J_SD'
 elif r.startswith('C_MCU'):ar='U_MCU';side=0
 elif r=='C_BUTTON':ar='SW_USER'
 elif r=='C_CC':ar='U_CC'
 elif r.startswith('C_IO'):ar='U_'+r[2:]
 elif r[2:] in placed:ar=r[2:]
 else:ar='U_IO0'
 supply_targets=[xy(z.GetPosition()) for z in fp[ar].Pads() if z.GetNetname()==p['pins'].get('1')]
 auto(r,[ar]+supply_targets[:1],side)
for p in parts:
 r=p['ref']
 if r in placed:continue
 ar,side='U_IO0',1
 if r.startswith(('R_MAIN','R_READY')):ar='U_MAIN'
 elif r.startswith(('R_CHG','R_TS','R_NTC','C_TS')):ar='U_BAT_WINDOW'
 elif r.startswith(('R_USB','R_CC')):ar='J_USB'
 elif r.startswith(('R_REF','R_VREF','D_REF')):ar='U_REF'
 elif r.startswith('R_BAT'):ar='Q_BAT_MEAS'
 elif r.startswith('R_CAM'):ar='J_CAM'
 elif r.startswith('R_SD'):ar='J_SD'
 elif r.startswith('R_LED'):ar='D_RGB'
 elif r.startswith('R_BUTTON'):ar='SW_USER'
 elif r.startswith(('R_BOOT0','R_STRAP')):ar='U_MCU'
 auto(r,[ar],side)
fp['L_CHARGER'].SetOrientationDegrees(180) # Physical body unchanged; switch terminal faces charger.
assert len(placed)==len(parts)
conflicts=[]
for side,items in occ.items():
 for i,(a,r) in enumerate(items):
  for z,rr in items[i+1:]:
   if r!=rr and not r.endswith(' TH') and not rr.endswith(' TH') and not r.endswith('thermal-via area') and not rr.endswith('thermal-via area') and overlaps(a,z):conflicts.append((r,rr,side))
assert not conflicts,conflicts
# Continuous ground planes on layers adjacent to all routing layers.
for layer,net,poly in [(k.In1_Cu,'GND',[(.4,.4),(W-.4,.4),(W-.4,H-.4),(.4,H-.4)]),(k.In4_Cu,'GND',[(.4,.4),(W-.4,.4),(W-.4,H-.4),(.4,H-.4)]),(k.In2_Cu,'3V3_A',[(.4,.4),(89.6,.4),(89.6,59.6),(.4,59.6)]),(k.In3_Cu,'3V3_SYS',[(.4,59.9),(64,59.9),(64,40),(99.6,40),(99.6,79.6),(.4,79.6)])]:
 z=k.ZONE(b);z.SetLayer(layer);z.SetNet(nets[net]);z.SetLocalClearance(mm(.2));z.SetPadConnection(k.ZONE_CONNECTION_FULL);z.SetMinThickness(mm(.15));z.SetThermalReliefGap(mm(.2));z.SetThermalReliefSpokeWidth(mm(.3));out=z.Outline();out.NewOutline()
 for x,y in poly:out.Append(mm(x),mm(y))
 z.SetZoneName(net+' layer'+str(layer));b.Add(z)
d=ds.m_NetSettings.m_DefaultNetClass;d.SetClearance(mm(.15));d.SetTrackWidth(mm(.15));d.SetViaDiameter(mm(.6));d.SetViaDrill(mm(.3))
b.BuildConnectivity();k.SaveBoard(str(P/'glove-v4-placement.kicad_pcb'),b)
rows=[]
for r,f in fp.items():
 z=placed[r];rows.append({'ref':r,'designator':refmap[r],'x_mm':xy(f.GetPosition())[0],'y_mm':xy(f.GetPosition())[1],'rotation_deg':f.GetOrientationDegrees(),'side':'B' if z['side'] else 'F','courtyard_mm':z['box'],'subsystem':by[r]['subsystem'],'body_bbox_mm':box(f,True),'footprint':by[r]['footprint']})
report={'status':'placement candidate; routing and DRC pending','board_mm':[W,H,1.6],'copper_layers':6,'stackup_function':['signal','GND','signal+analograil','signal+mainrail','GND','signal'],'retained_track_items':kept,'component_count':len(rows),'circuit_sha256':hashlib.sha256((E/'components.json').read_bytes()).hexdigest(),'parts':rows}
(P/'placement.json').write_text(json.dumps(report,indent=2)+'\n');print('PLACED',len(rows),'TRACKS',kept,'SIDES',Counter(x['side'] for x in rows),flush=True)
