from pathlib import Path
import pcbnew as k,math
from route_local4 import xy,route,layers
P=Path('/tmp/glove-eda-runtime/power-cad-fix');b=k.LoadBoard(str(P/'local.kicad_pcb'));a=(30.5,23.1);vv=sorted((math.dist(xy(t.GetPosition()),a),xy(t.GetPosition())) for t in b.GetTracks() if type(t)==k.PCB_VIA and t.GetNetname()=='GND');print(vv[:10],flush=True)
for _,q in vv[:10]:
 if route(b,'GND',a,[k.F_Cu],q,layers,step=.075,margin=6):
  k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();k.SaveBoard(str(P/'local.kicad_pcb'),b);k.WriteDRCReport(b,str(P/'ground.drc.txt'),k.EDA_UNITS_MILLIMETRES,True);s=(P/'ground.drc.txt').read_text();print(s[:1000],flush=True)
  if 'Found 0 unconnected pads' in s:break
