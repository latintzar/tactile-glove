from pathlib import Path
import pcbnew as k,math,re,sys,json
P=Path(__file__).resolve().parent
src=Path(sys.argv[1]);dst=Path(sys.argv[2]);b=k.LoadBoard(str(src));log=[]
for round in range(15):
 b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.WriteDRCReport(b,str(P/'cleanup.drc.txt'),k.EDA_UNITS_MILLIMETRES,True);s=(P/'cleanup.drc.txt').read_text();targets=[]
 for block in s.split('\n['):
  if not block.startswith('track_dangling]'):continue
  m=re.search(r'@\(([-\d.]+) mm, ([-\d.]+) mm\): Track \[(.*?)\] on (.*?), length ([\d.]+) mm',block)
  if not m:continue
  x,y,net,layer,length=m.groups();targets.append((float(x),float(y),net,b.GetLayerID(layer),float(length)))
 removed=0
 for x,y,n,l,length in targets:
  matches=[t for t in b.GetTracks() if type(t)!=k.PCB_VIA and t.GetNetname()==n and t.GetLayer()==l and math.dist((k.ToMM(t.GetPosition().x),k.ToMM(t.GetPosition().y)),(x,y))<.0002 and abs(k.ToMM(t.GetLength())-length)<.0002]
  for t in matches:b.RemoveNative(t);removed+=1
 log.append(removed);print('dangling cleanup',round,'removed',removed,flush=True)
 if not removed:break
b.SetFileName(str(dst));k.SaveBoard(str(dst),b);dst.with_suffix('.kicad_pro').write_bytes(src.with_suffix('.kicad_pro').read_bytes());k.WriteDRCReport(b,str(dst.with_suffix('.drc.txt')),k.EDA_UNITS_MILLIMETRES,True);dst.with_suffix('.cleanup.json').write_text(json.dumps(log))
