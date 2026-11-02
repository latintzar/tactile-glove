from pathlib import Path
import pcbnew as k,json
P=Path('/tmp/glove-eda-runtime/power-cad-fix');b=k.LoadBoard(str(P/'adapted.kicad_pcb'));rm=json.loads((P/'reference-map.json').read_text());rev={v:z for z,v in rm.items()};rows=[]
xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y))
for f in b.GetFootprints():
 pts=[]
 for g in f.GraphicalItems():
  if g.GetLayer() in [k.F_CrtYd,k.B_CrtYd]:q=g.GetBoundingBox();pts.extend([xy(q.GetOrigin()),xy(q.GetEnd())])
 if not pts:q=f.GetBoundingBox(False,False);pts=[xy(q.GetOrigin()),xy(q.GetEnd())]
 x,y=xy(f.GetPosition());bounds=[min(q[0] for q in pts),min(q[1] for q in pts),max(q[0] for q in pts),max(q[1] for q in pts)]
 rows.append(dict(ref=rev[f.GetReference()],designator=f.GetReference(),x_mm=x,y_mm=y,rotation_deg=f.GetOrientationDegrees(),side='B' if f.IsFlipped() else 'F',courtyard_mm=bounds,center_mm=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2]))
(P/'grouped-placement-candidate.json').write_text(json.dumps({'status':'V3.3 final 356-part placement; routing verification pending','board_mm':[90,60,1.6],'parts':rows},indent=2)+'\n')
