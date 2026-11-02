import faulthandler
faulthandler.enable()
from pathlib import Path
import pcbnew as k,json,math,collections,shutil
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from shapely.strtree import STRtree
P=Path('/tmp/glove-eda-runtime/power-cad-fix');SRC=next(a for a in Path(__file__).resolve().parents if (a / 'hardware/glove-v4').is_dir()) / 'hardware/glove-v3/electrical'
b=k.LoadBoard(str(SRC/'glove-v3-routed.kicad_pcb'));parts=json.loads((P/'components.json').read_text())['components'];rm=json.loads((P/'reference-map.json').read_text());rev={v:z for z,v in rm.items()};by={c['ref']:c for c in parts};fp={rev[f.GetReference()]:f for f in b.GetFootprints()};mm=k.FromMM;xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));vec=lambda p:k.VECTOR2I(mm(float(p[0])),mm(float(p[1])))
# All existing design rules, route geometry, antenna keepout, and zone boundaries survive.
names={n for c in parts for n in c['pins'].values() if n!='NC'};nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
for name in names:
 if name not in nets:n=k.NETINFO_ITEM(b,name);b.Add(n);nets[name]=n
for f in b.GetFootprints():
 for pad in f.Pads():
  if pad.GetNetname()=='VREF2V5':pad.SetNet(nets['VREF3V0'])
for t in b.GetTracks():
 if t.GetNetname()=='VREF2V5':t.SetNet(nets['VREF3V0'])
def courtyard(f):
 pts=[]
 for g in f.GraphicalItems():
  if g.GetLayer() in [k.F_CrtYd,k.B_CrtYd]:
   q=g.GetBoundingBox();pts.extend([xy(q.GetOrigin()),xy(q.GetEnd())])
 if not pts:
  q=f.GetBoundingBox(False,False);pts=[xy(q.GetOrigin()),xy(q.GetEnd())]
 return box(min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts))
def padshape(pad):
 cx,cy=xy(pad.GetPosition());w,h=xy(pad.GetSize());a=math.radians(-pad.GetOrientationDegrees());c,s=math.cos(a),math.sin(a)
 if pad.GetShape()==k.PAD_SHAPE_CIRCLE:return Point(cx,cy).buffer(w/2)
 return Polygon([(cx+x*c-y*s,cy+x*s+y*c) for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]])
tracks=list(b.GetTracks());trackgeom=[]
for t in tracks:
 g=Point(xy(t.GetPosition())).buffer(k.ToMM(t.GetWidth())/2) if type(t)==k.PCB_VIA else LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(k.ToMM(t.GetWidth())/2)
 trackgeom.append(g)
tree=STRtree(trackgeom);indices={id(g):i for i,g in enumerate(trackgeom)}
oldchanged=[];replace=['U_REF','C_ADC_REF']
anchors={'U_REF':(58,43),'C_ADC_REF':(55.5,44.5)}
for ref in replace:
 f=fp.pop(ref);oldchanged.extend([(p.GetNetname(),padshape(p),(k.B_Cu if f.IsFlipped() else k.F_Cu)) for p in f.Pads()]);b.Remove(f)
occupied={0:[],1:[]}
for f in fp.values():
 side=int(f.IsFlipped());g=courtyard(f).buffer(.05);occupied[side].append(g)
 if any(p.GetAttribute()==k.PAD_ATTRIB_PTH for p in f.Pads()):occupied[1-side].append(g)
for side in [0,1]:occupied[side].append(box(63,42,73.5,52))
changed=[];placements=[]
for ref in ['U_VMID','R_VMID_H','CDEC_U_REF','C_REF']:
 f=fp[ref]
 for pad in f.Pads():
  old=pad.GetNetname();new=by[ref]['pins'].get(pad.GetNumber(),'NC')
  if old!=new:changed.append(pad)
  pad.SetNetCode(0 if new=='NC' else nets[new].GetNetCode())
# Score small local moves by component proximity and how many existing traces must be repaired.
for ref in replace+[c['ref'] for c in parts if c['ref'] not in fp and c['ref'] not in replace]:
 print('PLACING',ref,flush=True)
 c=by[ref];f=k.FootprintLoad(str(P/'footprints'),c['footprint'].split(':')[1]);assert f,ref
 b.Add(f)
 f.SetReference(rm[ref]);f.SetValue(c.get('value',c['mpn']));f.SetFPID(k.LIB_ID('Glove',c['footprint'].split(':')[1]));f.Reference().SetVisible(False);f.Value().SetVisible(False)
 for pad in f.Pads():pad.SetNet(nets[c['pins'][pad.GetNumber()]])
 if ref.startswith('D_CLAMP_'):
  r=fp['RIN_'+ref[8:]];anchor=xy(next(p for p in r.Pads() if p.GetNumber()=='2').GetPosition());sides=[0,1]
 elif ref in anchors:anchor=anchors[ref];sides=[0] if ref=='U_REF' else [1,0]
 elif ref=='D_LDO_REV':anchor=(64,55.5);sides=[0,1]
 elif ref=='R_VMID_IN':anchor=(60,57);sides=[0,1]
 else:anchor=(54,55);sides=[0,1]
 best=None
 for radius in [3,5,8,14,25]:
  for side in sides:
   if f.IsFlipped()!=bool(side):f.Flip(vec((0,0)),False)
   for angle in [0,90,180,270]:
    f.SetOrientationDegrees(angle)
    for ix in range(max(2,int((anchor[0]-radius)*2)),min(178,int((anchor[0]+radius)*2))+1):
     for iy in range(max(2,int((anchor[1]-radius)*2)),min(118,int((anchor[1]+radius)*2))+1):
      pos=(ix/2,iy/2);d=math.dist(pos,anchor)
      if d>radius:continue
      f.SetPosition(vec(pos));g=courtyard(f)
      if not box(.55,.55,89.45,59.45).contains(g) or any(g.intersects(o) for o in occupied[side]):continue
      conflicts=0
      for pad in f.Pads():
       ps=padshape(pad).buffer(.16)
       for ti in tree.query(ps):
        t=tracks[int(ti)];tg=trackgeom[int(ti)]
        if t.GetNetCode()!=pad.GetNetCode() and (type(t)==k.PCB_VIA or pad.IsOnLayer(t.GetLayer())) and ps.intersects(tg):conflicts+=1
      score=d+conflicts*.3+(side!=sides[0])*.7
      if best is None or score<best[0]:best=(score,pos,angle,side)
  if best:break
 assert best,ref
 _,pos,angle,side=best
 if f.IsFlipped()!=bool(side):f.Flip(vec((0,0)),False)
 f.SetOrientationDegrees(angle);f.SetPosition(vec(pos));fp[ref]=f;occupied[side].append(courtyard(f).buffer(.05));changed.extend(f.Pads());placements.append({'ref':ref,'position':pos,'angle':angle,'side':side,'score':best[0]});print(placements[-1],flush=True)
# Removing copper that formerly entered moved/changed terminals is mandatory; router repairs remaining opens.
remove=set()
for i,(t,tg) in enumerate(zip(tracks,trackgeom)):
 for oldnet,g,layer in oldchanged:
  if t.GetNetname()==oldnet and (type(t)==k.PCB_VIA or t.GetLayer()==layer) and tg.intersects(g):remove.add(i);break
 for pad in changed:
  if t.GetNetCode()!=pad.GetNetCode() and (type(t)==k.PCB_VIA or pad.IsOnLayer(t.GetLayer())) and tg.intersects(padshape(pad).buffer(.16)):remove.add(i);break
for i in remove:b.Remove(tracks[i])
for ref,f in fp.items():
 c=by[ref];f.SetValue(c.get('value',c['mpn']));f.Reference().SetVisible(True);f.Reference().SetLayer(k.B_Fab if f.IsFlipped() else k.F_Fab);f.Reference().SetPosition(f.GetPosition());f.Reference().SetTextSize(vec((.7,.7)));f.Reference().SetTextThickness(mm(.1));f.Value().SetVisible(False)
 for g in f.GraphicalItems():
  if g.GetLayer() in [k.F_SilkS,k.B_SilkS]:g.SetLayer(k.B_Fab if f.IsFlipped() else k.F_Fab)
 for pad in f.Pads():
  new=c['pins'].get(pad.GetNumber(),'NC');pad.SetNetCode(0 if new=='NC' else nets[new].GetNetCode())
for z in b.Zones():z.UnFill()
b.BuildConnectivity();k.SaveBoard(str(P/'adapted.kicad_pcb'),b);assert k.ExportSpecctraDSN(b,str(P/'adapted.dsn'))
(P/'adapted-placement.json').write_text(json.dumps(placements,indent=2)+'\n')
print('Saved',len(fp),'components removedtracks',len(remove),'tracksremain',len(list(b.GetTracks())))
