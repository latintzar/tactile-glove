#!/usr/bin/env python3
import hashlib, json, math, re, sys
from pathlib import Path
import pcbnew
ORIGINAL=sys.argv[1]
CANDIDATE=sys.argv[2]
REPORT=sys.argv[3]
def mm(v): return pcbnew.ToMM(v)
def xy(p): return (mm(p.x),mm(p.y))
def board_hash(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def fpmap(b):
 out={}
 for f in b.GetFootprints():
  out[f.GetReference()]={'pos':xy(f.GetPosition()),'rot':f.GetOrientationDegrees(),'layer':f.GetLayerName(),'pads':[(p.GetNumber(),p.GetNetname(),xy(p.GetPosition()),(mm(p.GetSize().x),mm(p.GetSize().y))) for p in f.Pads()]}
 return out
def track_desc(t,b):
 if t.Type()==pcbnew.PCB_VIA_T:
  return {'kind':'via','uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'xy':xy(t.GetPosition()),'width':mm(t.GetWidth()),'drill':mm(t.GetDrillValue()),'layers':[b.GetLayerName(i) for i in t.GetLayerSet().Seq()]}
 return {'kind':'segment','uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'layer':b.GetLayerName(t.GetLayer()),'a':xy(t.GetStart()),'b':xy(t.GetEnd()),'width':mm(t.GetWidth())}
def zone_outline(z):
 rs=[]
 for i in range(z.Outline().OutlineCount()):
  c=z.Outline().COutline(i); rs.append([(c.GetPoint(j).x,c.GetPoint(j).y) for j in range(c.GetPointCount())])
 return rs
def polygon_area(rs):
 return sum(abs(sum(x*y2-x2*y for (x,y),(x2,y2) in zip(r,r[1:]+r[:1]))/2)/1e12 for r in rs)
def zone_desc(z,b):
 bb=z.GetBoundingBox(); r=zone_outline(z)
 return {'uuid':z.m_Uuid.AsString(),'net':z.GetNetname(),'layer_id':z.GetLayer(),'layer':b.GetLayerName(z.GetLayer()),'bbox_mm':(mm(bb.GetX()),mm(bb.GetY()),mm(bb.GetWidth()),mm(bb.GetHeight())),'outline_rings':[len(x) for x in r],'outline_area_mm2':polygon_area(r)}
def findzone(b,net): return next(z for z in b.Zones() if z.GetNetname()==net)
def hit(b,net,x,y):
 z=findzone(b,net); p=pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)); return bool(z.HitTestFilledArea(z.GetLayer(),p))
def drc(path):
 s=open(path).read()
 return {'via_dangling':s.count('[via_dangling]'),'track_dangling':s.count('[track_dangling]'),'unconnected_items':s.count('[unconnected_items]'),'shorting_items':s.count('[shorting_items]'),'clearance':s.count('[clearance]'),'copper_sliver':s.count('[copper_sliver]'),'unconnected_pads':int(re.search(r'Found (\d+) unconnected pads',s).group(1))}
bo=pcbnew.LoadBoard(ORIGINAL); bn=pcbnew.LoadBoard(CANDIDATE); fo,fn=fpmap(bo),fpmap(bn)
to={t.m_Uuid.AsString():track_desc(t,bo) for t in bo.GetTracks()}; tn={t.m_Uuid.AsString():track_desc(t,bn) for t in bn.GetTracks()}
removed=[to[k] for k in sorted(set(to)-set(tn))]; added=[tn[k] for k in sorted(set(tn)-set(to))]
zo={z.GetNetname():zone_desc(z,bo) for z in bo.Zones() if z.GetNetname() in ('USB_CHARGER_IN','VSYS')}; zn={z.GetNetname():zone_desc(z,bn) for z in bn.Zones() if z.GetNetname() in ('USB_CHARGER_IN','VSYS')}
pads_equal=all(fo[k]['pads']==fn[k]['pads'] for k in fo)
placements_equal=all(fo[k]['pos']==fn[k]['pos'] and fo[k]['rot']==fn[k]['rot'] and fo[k]['layer']==fn[k]['layer'] for k in fo)
orig_drc=drc(str(Path(ORIGINAL).with_suffix('.drc.txt'))); new_drc=drc(str(Path(CANDIDATE).with_suffix('.drc.txt')))
out={'source_hashes':{'original':board_hash(ORIGINAL),'candidate':board_hash(CANDIDATE)},'parts':{'original':len(fo),'candidate':len(fn),'refs_equal':set(fo)==set(fn),'placements_equal':placements_equal,'pads_nets_sizes_equal':pads_equal},'copper_delta':{'removed':removed,'added':added,'removed_count':len(removed),'added_track_count':sum(x['kind']=='segment' for x in added),'added_via_count':sum(x['kind']=='via' for x in added)},'zones':{'original':zo,'candidate':zn,'usb_outline_changed':zo['USB_CHARGER_IN']['outline_area_mm2']!=zn['USB_CHARGER_IN']['outline_area_mm2'],'vsys_outline_unchanged':zo['VSYS']['outline_rings']==zn['VSYS']['outline_rings'] and zo['VSYS']['outline_area_mm2']==zn['VSYS']['outline_area_mm2']},'native_connectivity':{'usb_charger_in_filled_on_power_a':findzone(bn,'USB_CHARGER_IN').IsFilled() and findzone(bn,'USB_CHARGER_IN').HasFilledPolysForLayer(findzone(bn,'USB_CHARGER_IN').GetLayer()),'u32_pin6':{'xy':xy(next(p for p in next(f for f in bn.GetFootprints() if f.GetReference()=='U32').Pads() if p.GetNumber()=='6').GetPosition()),'plane_hit_at_existing_via':hit(bn,'USB_CHARGER_IN',85.1229,57.5659)},'u42_pin24':{'xy':xy(next(p for p in next(f for f in bn.GetFootprints() if f.GetReference()=='U42').Pads() if p.GetNumber()=='24').GetPosition()),'new_via_plane_hit':hit(bn,'USB_CHARGER_IN',13.875,68.45)},'vsys_fill_not_compared':'saved-board audit establishes outline identity; fill equivalence is not inferred.'},'drc':{'original_saved':orig_drc,'candidate_saved':new_drc,'counts_equal':orig_drc==new_drc},'assessment':{'status':'PASS','no_native_regression':orig_drc==new_drc}}
# Fail closed if any material comparison fails; a report label is not a check.
assert set(fo)==set(fn) and len(fn)==561 and pads_equal and placements_equal
assert all(to[u]==tn[u] for u in set(to)&set(tn)), 'An existing track/via changed'
assert len(removed)==5 and all(x['net']=='USB_CHARGER_IN' for x in removed)
assert len(added)==9 and all(x['net']=='USB_CHARGER_IN' for x in added)
assert sum(x['kind']=='segment' and x['width']==.6 for x in added)==7
assert sum(x['kind']=='segment' and x['width']==.28 for x in added)==1
assert sum(x['kind']=='via' and x['width']==.4 and x['drill']==.2 for x in added)==1
oldzones={z.m_Uuid.AsString():z for z in bo.Zones()};newzones={z.m_Uuid.AsString():z for z in bn.Zones()}
assert oldzones.keys()==newzones.keys()
for uid,z in oldzones.items():
 n=newzones[uid]
 assert (z.GetLayer(),z.GetNetname(),z.GetAssignedPriority())==(n.GetLayer(),n.GetNetname(),n.GetAssignedPriority())
 if z.GetNetname()!='USB_CHARGER_IN':assert zone_outline(z)==zone_outline(n)
assert abs(zn['USB_CHARGER_IN']['outline_area_mm2']-zo['USB_CHARGER_IN']['outline_area_mm2']-.84)<1e-6
assert hit(bn,'USB_CHARGER_IN',85.1229,57.5659) and hit(bn,'USB_CHARGER_IN',13.875,68.45)
assert orig_drc==new_drc and new_drc['unconnected_pads']==20
assert not new_drc['shorting_items'] and not new_drc['clearance']
open(REPORT,'w').write(json.dumps(out,separators=(',',':'))+'\n')
print(json.dumps(out,indent=2))
