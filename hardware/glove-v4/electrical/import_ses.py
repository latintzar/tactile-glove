"""Import Specctra copper only using pcbnew; validates session placements first.
KiCad 7's Python ImportSpecctraSES binding requires a GUI board, so this small
headless importer uses the documented session routes and padstack geometry.
"""
from pathlib import Path
import math,re
import pcbnew as k
from sexpr import parse,child,children,atom

def import_session(board,filename):
 tree=parse(Path(filename).read_text());routes=child(tree,'routes');res=child(routes,'resolution');assert res[1]=='um';scale=1/(float(res[2])*1000)
 place=child(tree,'placement');pres=child(place,'resolution');pscale=1/(float(pres[2])*1000);fps={f.GetReference():f for f in board.GetFootprints()}
 for comp in children(place,'component'):
  for p in children(comp,'place'):
   ref=atom(p[1]);f=fps[ref];x=float(p[2])*pscale;y=-float(p[3])*pscale
   assert math.hypot(k.ToMM(f.GetPosition().x)-x,k.ToMM(f.GetPosition().y)-y)<.002,(ref,'unexpected movement')
   assert f.IsFlipped()==(p[4]=='back'),(ref,'side changed')
 netmap={n.GetNetname():n for n in board.GetNetsByNetcode().values()}
 padstacks={atom(p[1]):p for p in children(child(routes,'library_out'),'padstack')}
 for item in list(board.GetTracks()):board.RemoveNative(item)
 counts={'segments':0,'vias':0}
 for net in children(child(routes,'network_out'),'net'):
  n=netmap[atom(net[1])]
  for w in children(net,'wire'):
   path=child(w,'path');layer=board.GetLayerID(atom(path[1]));width=float(path[2])*scale;coords=[float(a)*scale for a in path[3:]];assert len(coords)%2==0
   for i in range(0,len(coords)-2,2):
    a=k.VECTOR2I(k.FromMM(coords[i]),k.FromMM(-coords[i+1]));z=k.VECTOR2I(k.FromMM(coords[i+2]),k.FromMM(-coords[i+3]))
    if a==z:continue
    t=k.PCB_TRACK(board);t.SetStart(a);t.SetEnd(z);t.SetLayer(layer);t.SetWidth(k.FromMM(width));t.SetNet(n);board.Add(t);counts['segments']+=1
  for v in children(net,'via'):
   name=atom(v[1]);stack=padstacks[name];shapes=[child(s,'circle') for s in children(stack,'shape')];assert all(shapes),'Only circular through-vias supported'
   diam=float(shapes[0][2])*scale;drill=re.search(r':([\d.]+)_um',name);assert drill,('missing drill',name)
   t=k.PCB_VIA(board);t.SetPosition(k.VECTOR2I(k.FromMM(float(v[2])*scale),k.FromMM(-float(v[3])*scale)));t.SetWidth(k.FromMM(diam));t.SetDrill(k.FromMM(float(drill[1])/1000));t.SetViaType(k.VIATYPE_THROUGH);t.SetLayerPair(k.F_Cu,k.B_Cu);t.SetNet(n);board.Add(t);counts['vias']+=1
 board.BuildConnectivity();return counts
