from pathlib import Path
import pcbnew as k,json
from route_local4 import route,layers
P=Path('/tmp/glove-eda-runtime/power-cad-fix');b=k.LoadBoard(str(P/'local.kicad_pcb'));r=route(b,'CHG_IN_R3',(37,9.5),[k.B_Cu],(40.925,15.6),layers,step=.075,margin=8);assert r
k.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();k.SaveBoard(str(P/'local.kicad_pcb'),b);k.WriteDRCReport(b,str(P/'last.drc.txt'),k.EDA_UNITS_MILLIMETRES,True)
