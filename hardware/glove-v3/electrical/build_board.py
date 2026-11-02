"""Build an editable KiCad floorplan from canonical parts and verified pad geometry.
This file is a placement source, not a fabrication release. Routing/DRC follow separately.
"""
from pathlib import Path
import json,math
import pcbnew as k
P=Path(__file__).parent;parts=json.loads((P/'components.json').read_text())['components'];refs=json.loads((P/'reference-map.json').read_text())
b=k.BOARD();b.SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(k.FromMM(1.6))
mm=k.FromMM;vec=lambda x,y:k.VECTOR2I(mm(x),mm(y))
netnames=sorted({n for p in parts for n in p['pins'].values() if n!='NC'});nets={}
for i,n in enumerate(netnames,1):nets[n]=k.NETINFO_ITEM(b,n,i);b.Add(nets[n])
W,H=70,46
for (x1,y1,x2,y2) in [(0,0,W,0),(W,0,W,H),(W,H,0,H),(0,H,0,0)]:
 e=k.PCB_SHAPE();e.SetShape(k.SHAPE_T_SEGMENT);e.SetStart(vec(x1,y1));e.SetEnd(vec(x2,y2));e.SetLayer(k.Edge_Cuts);e.SetWidth(mm(.05));b.Add(e)
free={0:[(1,1,W-1,H-1)],1:[(1,1,W-1,H-1)]};occupied={0:[],1:[]};fp={};bounds={};placement=[]
def overlap(a,z):return a[0]<z[2]-1e-6 and a[2]>z[0]+1e-6 and a[1]<z[3]-1e-6 and a[3]>z[1]+1e-6
def reserve(side,r,name):
 global free
 new=[]
 for a in free[side]:
  if not overlap(a,r):new.append(a);continue
  x,y,X,Y=a;u,v,U,V=r
  if u>x:new.append((x,y,u,Y))
  if U<X:new.append((U,y,X,Y))
  if v>y:new.append((x,y,X,v))
  if V<Y:new.append((x,V,X,Y))
 free[side]=[a for i,a in enumerate(new) if a[2]-a[0]>.05 and a[3]-a[1]>.05 and not any(i!=j and z[0]<=a[0] and z[1]<=a[1] and z[2]>=a[2] and z[3]>=a[3] and (a!=z or j<i) for j,z in enumerate(new))]
 occupied[side].append((r,name))
for p in parts:
 f=k.FootprintLoad(str(P/'footprints'),p['footprint'].split(':')[1]);f.SetReference(refs[p['ref']]);f.SetValue(p['mpn']);f.Value().SetVisible(False);f.Reference().SetTextSize(vec(.55,.55));f.Reference().SetTextThickness(mm(.1));f.Reference().SetVisible(False)
 for pad in f.Pads():
  n=p['pins'].get(pad.GetNumber());
  if n and n!='NC':pad.SetNet(nets[n])
 b.Add(f);fp[p['ref']]=f
 pts=[]
 for g in f.GraphicalItems():
  if g.GetLayer()==k.F_CrtYd:
   box=g.GetBoundingBox();pts.extend([(k.ToMM(box.GetLeft()),k.ToMM(box.GetTop())),(k.ToMM(box.GetRight()),k.ToMM(box.GetBottom()))])
 if not pts:
  bb=f.GetBoundingBox(False,False);pts=[(k.ToMM(bb.GetLeft()),k.ToMM(bb.GetTop())),(k.ToMM(bb.GetRight()),k.ToMM(bb.GetBottom()))]
 bounds[p['ref']]=(min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts))
def place(ref,cx,cy,angle,side):
 f=fp[ref];x,y,X,Y=bounds[ref];w,h=X-x,Y-y
 # Center placement relative to exact footprint courtyard center.
 dx=(x+X)/2;dy=(y+Y)/2;t=math.radians(angle)
 if side: f.Flip(vec(0,0),False);dx=-dx
 f.SetOrientationDegrees(angle);f.SetPosition(vec(cx-(dx*math.cos(t)+dy*math.sin(t)),cy-(-dx*math.sin(t)+dy*math.cos(t))))
 if angle%180:w,h=h,w
 r=(cx-w/2-.15,cy-h/2-.15,cx+w/2+.15,cy+h/2+.15)
 hits=[n for a,n in occupied[side] if overlap(a,r)]
 if hits:raise ValueError((ref,'collision',hits,r))
 reserve(side,r,ref);placement.append({'ref':ref,'designator':refs[ref],'x_mm':round(k.ToMM(f.GetPosition().x),4),'y_mm':round(k.ToMM(f.GetPosition().y),4),'rotation_deg':angle,'side':'B' if side else 'F','courtyard_mm':r})
# Corner fastener clearances and radio region on both sides.
for side in [0,1]:
 for x,y in [(3,3),(67,3),(3,43),(67,43)]:reserve(side,(x-2.2,y-2.2,x+2.2,y+2.2),'M2 keepout')
# Module exact pad geometry is offset from its outline. Separate radio keepout retained in floorplan.
fixed=[('J_XIAO',54.5,34.3,180,0),('J_THUMB',12,5,0,0),('J_INDEX',27,5,0,0),('J_MIDDLE',43,5,0,0),('J_RING',59,11,0,0),('J_LITTLE',12,13,0,0),('J_PALM_HEEL',35,13,0,0),('SW1',13,40,0,0),('SW2',27,40,0,0),('J_BAT',40,40,0,0),('J_OLED',39,33,0,0),('J_IMU',9,24,90,0)]
for z in fixed:place(*z)
# The module underside is occupied by its castellated/bottom contacts; no bottom parts here.
reserve(1,(48,21,65,29),'radio copper/component keepout')
# Antenna keepout will be refined against Seeed V1.1 geometry and ground-plane projection.
# Pack exact courtyards, large ICs first, then passives. Every overlap is checked independently below.
fixedrefs={x[0] for x in fixed};remaining=[p for p in parts if p['ref'] not in fixedrefs]
remaining.sort(key=lambda p: -(bounds[p['ref']][2]-bounds[p['ref']][0])*(bounds[p['ref']][3]-bounds[p['ref']][1]))
for p in remaining:
 ref=p['ref'];x,y,X,Y=bounds[ref];w,h=X-x+.3,Y-y+.3;candidates=[]
 for side in [0,1]:
  for a in free[side]:
   for rot,ww,hh in [(0,w,h),(90,h,w)]:
    aw,ah=a[2]-a[0],a[3]-a[1]
    if ww<=aw+1e-6 and hh<=ah+1e-6:
     score=(min(aw-ww,ah-hh),max(aw-ww,ah-hh),side)
     candidates.append((score,a[0]+ww/2,a[1]+hh/2,rot,side))
 if not candidates:raise RuntimeError(f'No collision-free placement for {ref}; enlarge board or revise layout')
 _,cx,cy,rot,side=min(candidates);place(ref,cx,cy,rot,side)
# Independently compare final courtyard rectangles (including arbitrary fixed orientations).
for side in [0,1]:
 for i,(r,n) in enumerate(occupied[side]):
  for z,m in occupied[side][i+1:]:
   assert not overlap(r,z),(n,m)
# Actual M2 clearance holes; no purchased component implied.
for i,(x,y) in enumerate([(3,3),(67,3),(3,43),(67,43)],1):
 f=k.FOOTPRINT(b);f.SetReference('H'+str(i));pad=k.PAD(f);pad.SetAttribute(k.PAD_ATTRIB_NPTH);pad.SetShape(k.PAD_SHAPE_CIRCLE);pad.SetSize(vec(2.2,2.2));pad.SetDrillSize(vec(2.2,2.2));pad.SetLayerSet(k.LSET.AllCuMask());f.Add(pad);f.SetPosition(vec(x,y));b.Add(f)
k.SaveBoard(str(P/'glove-v3-floorplan.kicad_pcb'),b)
(P/'placement-candidate.json').write_text(json.dumps({'status':'collision-free floorplan; routing and electrical placement review pending','board_mm':[W,H,1.6],'parts':placement},indent=2))
print('Placed',len(placement),'verified footprints on',W,'x',H,'mm; F:',sum(x['side']=='F' for x in placement),'B:',sum(x['side']=='B' for x in placement))
