"""Measure current-BOM courtyard packing area; this is not a product minimum."""
from pathlib import Path
import pcbnew as k,json,hashlib,sys,os
from shapely.geometry import Polygon
from shapely.ops import unary_union
E=Path(sys.argv[1]);board=E/'glove-v4-routing-candidate.kicad_pcb';b=k.LoadBoard(str(board));sides={'F':[],'B':[]};parts=[];missing=[]
for f in b.GetFootprints():
 f.BuildCourtyardCaches();side='B' if f.IsFlipped() else 'F';q=f.GetCourtyard(k.B_CrtYd if f.IsFlipped() else k.F_CrtYd);polys=[]
 for i in range(q.OutlineCount()):
  out=q.COutline(i);ext=[(k.ToMM(out.CPoint(j).x),k.ToMM(out.CPoint(j).y)) for j in range(out.PointCount())];holes=[]
  for h in range(q.HoleCount(i)):
   inner=q.CHole(i,h);holes.append([(k.ToMM(inner.CPoint(j).x),k.ToMM(inner.CPoint(j).y)) for j in range(inner.PointCount())])
  polys.append(Polygon(ext,holes))
 if not polys:missing.append(f.GetReference());continue
 g=unary_union(polys);sides[side].append((f.GetReference(),g));parts.append({'designator':f.GetReference(),'side':side,'courtyard_polygon_mm2':g.area,'aabb_mm2':g.envelope.area})
summary={};overlaps=[]
for side,items in sides.items():
 for i,(a,g) in enumerate(items):
  for c,h in items[i+1:]:
   area=g.intersection(h).area
   if area>1e-6:overlaps.append({'side':side,'parts':[a,c],'intersection_mm2':area})
 summary[side]={'sum_polygon_mm2':sum(g.area for _,g in items),'union_mm2':unary_union([g for _,g in items]).area,'sum_aabb_mm2':sum(g.envelope.area for _,g in items)}
report={'board_sha256':hashlib.sha256(board.read_bytes()).hexdigest(),'method':'Actual KiCad cached courtyard polygon areas, separately for the installed side; polygon intersections detect overlaps. Polygon arcs use KiCad tessellation. AABB values are reported separately and are not a rigorous packing lower bound.','current_bom_parts':len(list(b.GetFootprints())),'missing_courtyards':missing,'by_side':summary,'sum_courtyard_polygon_mm2':sum(x['sum_polygon_mm2'] for x in summary.values()),'same_side_overlap_pairs':overlaps,'requested_footprint_mm':[50.8,38.1],'requested_two_faces_area_mm2':2*50.8*38.1,'interpretation':'Current BOM only. Courtyard area requires two faces at minimum, before routing channels, antenna clearance, edge access, harness mating, or battery. This does not establish the minimum achievable rearchitected product.'}
report['conservative_area_excluding_all_connectors_and_mcu_courtyard_mm2']=sum(x['courtyard_polygon_mm2'] for x in parts if not x['designator'].startswith('J') and x['designator']!='U51');report['rf_courtyard_note']='The MCU courtyard includes its external antenna exclusion region and extends beyond the PCB. It is excluded entirely, along with every connector, from the conservative area bound.'
report['sum_polygon_to_target_two_faces_ratio']=report['sum_courtyard_polygon_mm2']/report['requested_two_faces_area_mm2'];tmp=E/'size-feasibility.json.tmp';tmp.write_text(json.dumps(report,indent=2)+'\n');os.chown(tmp,1003,1003);os.replace(tmp,E/'size-feasibility.json');print(json.dumps(report,indent=2))
