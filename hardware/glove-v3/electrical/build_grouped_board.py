"""Rebuild the electrically grouped four-layer glove PCB from canonical parts.
KiCad 7 pcbnew is required. Routing is performed by route_board.py afterwards.
"""
from pathlib import Path
from collections import defaultdict
import json, math
import pcbnew as k
P=Path(__file__).parent
parts=json.loads((P/'components.json').read_text())['components']
refmap=json.loads((P/'reference-map.json').read_text())
byref={p['ref']:p for p in parts}
b=k.BOARD();b.SetCopperLayerCount(4)
mm=k.FromMM;vec=lambda x,y:k.VECTOR2I(mm(x),mm(y))
ds=b.GetDesignSettings();ds.SetBoardThickness(mm(1.6));ds.m_MinClearance=mm(.15);ds.m_TrackMinWidth=mm(.15);ds.m_ViasMinSize=mm(.6);ds.m_MinThroughDrill=mm(.3);ds.m_ViasMinAnnularWidth=mm(.15);ds.m_HoleToHoleMin=mm(.25)
netnames=sorted({n for p in parts for n in p['pins'].values() if n!='NC'})
nets={n:k.NETINFO_ITEM(b,n,i) for i,n in enumerate(netnames,1)}
for n in nets.values():b.Add(n)
W,H=90,60
for a,z in [((0,0),(W,0)),((W,0),(W,H)),((W,H),(0,H)),((0,H),(0,0))]:
 e=k.PCB_SHAPE();e.SetShape(k.SHAPE_T_SEGMENT);e.SetStart(vec(*a));e.SetEnd(vec(*z));e.SetLayer(k.Edge_Cuts);e.SetWidth(mm(.05));b.Add(e)
fp={};bounds={};occupied={0:[],1:[]};placement={};padnets=defaultdict(list)
def overlap(a,z):return a[0]<z[2]-1e-6 and a[2]>z[0]+1e-6 and a[1]<z[3]-1e-6 and a[3]>z[1]+1e-6
for p in parts:
 f=k.FootprintLoad(str(P/'footprints'),p['footprint'].split(':')[1])
 if not f:raise RuntimeError('Cannot load '+p['footprint'])
 f.SetReference(refmap[p['ref']]);f.SetValue(p['mpn']);f.Value().SetVisible(False);f.Reference().SetVisible(False)
 f.SetFPID(k.LIB_ID('Glove',p['footprint'].split(':')[1]))
 for pad in f.Pads():
  n=p['pins'].get(pad.GetNumber())
  if n and n!='NC':pad.SetNet(nets[n]);padnets[n].append((p['ref'],pad))
 b.Add(f);fp[p['ref']]=f;pts=[]
 for g in f.GraphicalItems():
  if g.GetLayer()==k.F_CrtYd:
   box=g.GetBoundingBox();pts += [(k.ToMM(box.GetLeft()),k.ToMM(box.GetTop())),(k.ToMM(box.GetRight()),k.ToMM(box.GetBottom()))]
 if not pts:
  box=f.GetBoundingBox(False,False);pts=[(k.ToMM(box.GetLeft()),k.ToMM(box.GetTop())),(k.ToMM(box.GetRight()),k.ToMM(box.GetBottom()))]
 bounds[p['ref']]=(min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts))
def rect(ref,cx,cy,angle,margin=.10):
 x,y,X,Y=bounds[ref];w,h=X-x,Y-y
 if angle%180:w,h=h,w
 return (cx-w/2-margin,cy-h/2-margin,cx+w/2+margin,cy+h/2+margin)
def legal(r,side):return r[0]>=.45 and r[1]>=.45 and r[2]<=W-.45 and r[3]<=H-.45 and not any(overlap(r,a) for a,n in occupied[side])
def place(ref,cx,cy,angle,side):
 r=rect(ref,cx,cy,angle)
 if not legal(r,side):raise ValueError((ref,r,[(n,a) for a,n in occupied[side] if overlap(r,a)]))
 f=fp[ref];x,y,X,Y=bounds[ref];dx=(x+X)/2;dy=(y+Y)/2;t=math.radians(angle)
 if side:f.Flip(vec(0,0),False);dx=-dx
 f.SetOrientationDegrees(angle);f.SetPosition(vec(cx-(dx*math.cos(t)+dy*math.sin(t)),cy-(-dx*math.sin(t)+dy*math.cos(t))))
 occupied[side].append((r,ref))
 placement[ref]={'ref':ref,'designator':refmap[ref],'x_mm':round(k.ToMM(f.GetPosition().x),4),'y_mm':round(k.ToMM(f.GetPosition().y),4),'rotation_deg':angle,'side':'B' if side else 'F','courtyard_mm':r,'center_mm':[cx,cy]}
 # Through-hole bodies are a bottom component keepout as well.
 if any(p.GetAttribute()==k.PAD_ATTRIB_PTH for p in f.Pads()):occupied[1-side].append((r,ref+' through-hole keepout'))
# Front sensor connectors along the finger-facing edge.
fixed=[('J_INDEX',11,4.4,0,0),('J_MIDDLE',28,4.4,0,0),('J_RING',45,4.4,0,0),('J_LITTLE',62,4.4,0,0),('J_THUMB',79,4.4,0,0),
 ('J_PALM_HEEL',12.5,51,0,0),('J_BAT',6,43.5,0,0),('J_IMU',7,53,0,1),('J_OLED',29.5,56,180,0),('SW1',44,56.5,0,0),('J_XIAO',77.9,49.4,270,0),
 ('U_MUX1',15,33.5,90,0),('U_MUX2',34,33.5,90,0),('U_MUX3',53,33.5,90,0),('U_MUX4',72,33.5,90,0),
 ('U_BANK1',28,46.5,0,0),('U_MUX_FINAL',41,47.5,90,0),('U_ADC_DRV',50,47,0,0),('U_ADC_NEG',50,52,0,0),('U_ADC',58,49,0,0),('U_REF',58,43,0,0),('U_VMID',58,55.5,0,0),('U_LDO',64,57.5,0,0),('U_LOAD',64,53.8,0,0),('U_IOX',25,51,0,1),('U_MUX_ADDR',39,50,0,1)]
for z in fixed:
 if z[0] in byref:place(*z)
channels=['I1','I2','I3','M1','M2','M3','R1','R2','R3','L1','L2','L3','T1','T2','P1','P2','P3','P4','H1','H2']
for i in range(5):
 cx=10+17.5*i
 place('U_CHG'+str(i+1),cx,17.5,0,0)
 for j in range(2):place('U_FILT'+str(2*i+j+1),cx,14.5+19*j,0,1)
# Component and copper keepout at the module antenna-facing board edge.
# The canonical module outline is 21 x 17.8 mm, USB at the opposite end.
for side in (0,1):occupied[side].append(((63,42,73.5,52),'antenna component keepout'))
# Placement objective: retain critical components beside the actual amplifier pins.
def padpos(p):return k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y)
def autoplacement(ref,anchor_refs,side,preferred=None):
 p=byref[ref];targets=[]
 for n in p['pins'].values():
  if n in ('GND','3V3','3V3A','1V8','VREF2V5','VEXC2V5','VMID1V25'):continue
  targets += [(padpos(pad),4 if r in anchor_refs else 1) for r,pad in padnets[n] if r in placement and (r in anchor_refs or r.startswith(('R','C'))) ]
 for ar in anchor_refs:
  a=placement[ar]['center_mm'];targets.append((a,2))
 if preferred:targets.append((preferred,8))
 if not targets:targets=[((45,49),1)]
 tot=sum(t[1] for t in targets);tx=sum(t[0][0]*t[1] for t in targets)/tot;ty=sum(t[0][1]*t[1] for t in targets)/tot
 best=None
 for radius in (5,9,15,25,100):
  for ix in range(max(2,math.floor((tx-radius)*2)),min(179,math.ceil((tx+radius)*2))+1):
   cx=ix/2
   for iy in range(max(2,math.floor((ty-radius)*2)),min(119,math.ceil((ty+radius)*2))+1):
    cy=iy/2
    for angle in (0,90):
     r=rect(ref,cx,cy,angle)
     if not legal(r,side):continue
     score=sum(math.hypot(cx-a[0],cy-a[1])*w for a,w in targets)+.005*(cx+cy)
     if best is None or score<best[0]:best=(score,cx,cy,angle)
  if best:break
 if not best:raise RuntimeError('No position '+ref)
 _,cx,cy,angle=best;place(ref,cx,cy,angle,side)
# Feedback components and series input resistors remain on the charge IC side.
for ci,c in enumerate(channels):
 u='U_CHG'+str(ci//4+1)
 for stem in ('RFB_','CFB_','RIN_'):autoplacement(stem+c,[u],0)
# Decoupling placed before the low-priority support components.
for p in parts:
 r=p['ref']
 if r.startswith('CDEC_'):
  u=r[5:];side=1 if placement[u]['side']=='B' else 0
  supply=[padpos(pad) for pad in fp[u].Pads() if pad.GetNetname() in ('3V3A','3V3')]
  autoplacement(r,[u],side,supply[0] if supply else None)
autoplacement('C_MUX_ADDR',['U_MUX_ADDR'],1)
# ADC charge bucket and supply/reference network directly beneath the converter.
for z in [('C_ADC_REF',55.5,44.5,0,1),('C_ADC_AVDD',55.5,47.5,0,1),('C_ADC_DVIO',60,47.5,0,1),('R_ADC_ISO',52,48.5,0,1),('R_ADC_NEG_ISO',52,51.5,0,1),('C_ADC_BUCKET',56,50.5,90,1),('C_ADC_NEG_BUCKET',58,50.5,90,1)]:place(*z)
for ci,c in enumerate(channels):
 u='U_FILT'+str(ci//2+1)
 for stem in ('RS1B_','CS1G_','CS1FB_','RS1A_','RS2B_','CS2G_','CS2FB_','RS2A_'):autoplacement(stem+c,[u],1)
# Pressure pulldowns next to their cable connectors.
conn={c:next(p['ref'] for p in parts if p['ref'].startswith('J_') and 'PRESS_'+c in p['pins'].values()) for c in channels}
for c in channels:autoplacement('RPD_'+c,[conn[c]],0)
support={
 'C_LDO_IN':'U_LDO','C_LDO_OUT':'U_LDO','C_REF':'U_REF','C_ADC_AVDD':'U_ADC','C_ADC_DVIO':'U_ADC','C_ADC_REF':'U_ADC',
 'R_VMID_H':'U_VMID','R_VMID_L':'U_VMID','C_VMID':'U_VMID','R_ADC_ISO':'U_ADC_DRV','C_ADC_BUCKET':'U_ADC',
 'R_ADC_NEG_ISO':'U_ADC_NEG','C_ADC_NEG_BUCKET':'U_ADC','R_ANALOG_EN':'U_LOAD','C_LOAD_IN':'U_LOAD','C_LOAD_OUT':'U_LOAD',
 'R_I2C_SDA':'U_IOX','R_I2C_SCL':'U_IOX','R_WAKE':'U_IOX','R_BTN0':'SW1','R_RGB_CS':'J_OLED'}
for p in parts:
 r=p['ref']
 if r in placement:continue
 u=support.get(r,'J_XIAO');side=1 if placement[u]['side']=='B' else 0
 autoplacement(r,[u],side)
assert len(placement)==len(parts)
# Independent rectangle overlap check.
for side in (0,1):
 for i,(r,n) in enumerate(occupied[side]):
  for z,m in occupied[side][i+1:]:
   if 'antenna' in n or 'antenna' in m:continue
   assert not overlap(r,z),(n,m)
# Plane regions terminate before the antenna keepout. Routed power connects via
# stitched vias added by route_board.py; plane fill is performed before final DRC.
for layer,net in [(k.In1_Cu,'GND'),(k.In2_Cu,'3V3A')]:
 z=k.ZONE(b);z.SetLayer(layer);z.SetNet(nets[net]);z.SetLocalClearance(mm(.2));z.SetThermalReliefGap(mm(.2));z.SetThermalReliefSpokeWidth(mm(.3));z.SetMinThickness(mm(.15));z.SetPadConnection(k.ZONE_CONNECTION_FULL)
 out=z.Outline();out.NewOutline()
 for x,y in [(.4,.4),(89.6,.4),(89.6,59.6),(.4,59.6)]:out.Append(mm(x),mm(y))
 z.SetZoneName(net+' internal plane');b.Add(z)
# Complete radio-area rule keepout across all four copper layers.
z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayerSet(k.LSET.AllCuMask(4));z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowCopperPour(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
out=z.Outline();out.NewOutline()
for x,y in [(63,42),(73.5,42),(73.5,52),(63,52)]:out.Append(mm(x),mm(y))
z.SetZoneName('XIAO antenna edge clearance');b.Add(z)
k.SaveBoard(str(P/'glove-v3-grouped.kicad_pcb'),b)
(P/'grouped-placement-candidate.json').write_text(json.dumps({'status':'electrically grouped placement; routing and DRC follow separately','board_mm':[W,H,1.6],'parts':list(placement.values())},indent=2))
print('Placed',len(placement),'parts; front',sum(p['side']=='F' for p in placement.values()),'back',sum(p['side']=='B' for p in placement.values()))
