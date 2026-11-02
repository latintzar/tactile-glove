"""Unapplied copper-only proposal; canonical input and component placement unchanged."""
from pathlib import Path
import pcbnew as k,json,hashlib,shutil,sys
SRC=Path(sys.argv[1]).resolve()
DST=Path(sys.argv[2]).resolve();DST.parent.mkdir(parents=True,exist_ok=True)
assert SRC != DST, "Source must remain unchanged"
assert hashlib.sha256(SRC.read_bytes()).hexdigest()=='53d0d956f016748fcdcfb6cd0ae84dfd56f47e43a227efb4d26c83fc53c5bcb5'
shutil.copyfile(SRC.with_suffix('.kicad_pro'),DST.with_suffix('.kicad_pro'))
b=k.LoadBoard(str(SRC));mm=k.FromMM;v=lambda x,y:k.VECTOR2I(mm(x),mm(y))
tracks={t.m_Uuid.AsString():t for t in b.GetTracks()};log=[]
for ident in ['f7567b7f-d7fa-42e6-90d5-df22c782dbd6','0ac1b947-f91e-4ee0-81db-c7fa052cda46']:
 t=tracks[ident];assert t.GetNetname()=='USB_CHARGER_IN' and t.GetLayer()==k.F_Cu and t.GetWidth()==mm(.15)
 b.RemoveNative(t);log.append({'action':'remove_old_output','uuid':ident,'old_width_mm':.15})
for ident in ['44221b70-f6ef-4b29-8e23-b4451a89309f','5250f0f1-fc4f-46c2-aa92-7e592a62a6a3','8d667235-9f45-4b5e-97dd-d97acb38dc1b']:
 t=tracks[ident];assert t.GetNetname()=='USB_CHARGER_IN' and t.GetWidth()==mm(.28)
 b.RemoveNative(t);log.append({'action':'remove_detour','uuid':ident})
net=b.FindNet('USB_CHARGER_IN')
route=json.loads((Path(__file__).parent/'output-route.json').read_text())
for a,e in zip(route,route[1:]):
 t=k.PCB_TRACK(b);t.SetStart(v(*a));t.SetEnd(v(*e));t.SetWidth(mm(.6));t.SetLayer(k.F_Cu);t.SetNet(net);b.Add(t)
 log.append({'action':'output_route','a':a,'b':e,'width_mm':.6,'uuid':t.m_Uuid.AsString()})
t=k.PCB_TRACK(b);t.SetStart(v(14.025,68.25));t.SetEnd(v(13.875,68.45));t.SetWidth(mm(.28));t.SetLayer(k.F_Cu);t.SetNet(net);b.Add(t)
log.append({'action':'short_fanout','a':[14.025,68.25],'b':[13.875,68.45],'width_mm':.28,'uuid':t.m_Uuid.AsString()})
z=k.PCB_VIA(b);z.SetPosition(v(13.875,68.45));z.SetWidth(mm(.4));z.SetDrill(mm(.2));z.SetViaType(k.VIATYPE_THROUGH);z.SetLayerPair(k.F_Cu,k.B_Cu);z.SetNet(net);b.Add(z)
log.append({'action':'add_via','xy':[13.875,68.45],'diameter_mm':.4,'drill_mm':.2,'uuid':z.m_Uuid.AsString(),'process':'filled/capped via overlaps U42 pin24 solder land'})
zone=next(z for z in b.Zones() if z.GetNetname()=='USB_CHARGER_IN' and z.GetLayer()==3)
assert zone.GetAssignedPriority()==2
old=[(k.ToMM(zone.Outline().COutline(0).CPoint(i).x),k.ToMM(zone.Outline().COutline(0).CPoint(i).y)) for i in range(zone.Outline().COutline(0).PointCount())]
outline=[(84.4,52),(99.6,52),(99.6,79.6),(13,79.6),(13,68.8),(13.35,68.8),(13.35,68),(14.4,68),(14.4,68.8),(21.5,68.8),(21.5,73.5),(84.4,73.5)]
q=k.SHAPE_POLY_SET();q.NewOutline()
for x,y in outline:q.Append(mm(x),mm(y))
zone.SetOutline(q)
log.append({'action':'extend_usb_plane_to_via','layer':'POWER_A','net':'USB_CHARGER_IN','old_outline':old,'new_outline':outline,'added_area_mm2':.84})
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());b.SetFileName(str(DST));k.SaveBoard(str(DST),b)
k.WriteDRCReport(b,str(DST.with_suffix('.drc.txt')),k.EDA_UNITS_MILLIMETRES,True)
DST.with_suffix('.changes.json').write_text(json.dumps(log,indent=2)+'\n')
print(DST,hashlib.sha256(DST.read_bytes()).hexdigest())
