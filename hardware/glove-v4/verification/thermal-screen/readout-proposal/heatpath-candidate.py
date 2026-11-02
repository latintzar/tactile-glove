#!/usr/bin/env python3
"""Unapplied roof insert / MCU-shield bridge concept and exact envelope checks."""
import sys,json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;V=H.parents[2];E=V/'enclosure'
sys.path.insert(0,str(E));import verify_enclosure as a
m=json.loads((E/'print-manifest.json').read_text());c=json.loads((E/'component-envelopes.json').read_text())
parts={p['ref']:a.solid(p['positions'],p['triangles']) for p in c['main_board']['parts']}
for n in m['manufactured_parts']:
 t=a.trimesh.load_mesh(E/n,process=True);parts[n]=a.solid(t.vertices,t.faces)
plate=a.box(92,64,1.5,54,30,44.75)+a.box(14,12.5,1.5,91,68.25,44.75)
# A supported U saddle, formed or machined Al, under the tongue.
bridge=a.box(12,10,1.2,90,67,35.1)+a.box(1.2,10,5.3,84.6,67,38.35)+a.box(1.2,10,5.3,95.4,67,38.35)+a.box(14,10,3,90,67,42.5)
rf=a.box(48,21,46,89.75,90.5,23)
rows={}
for name,s in {'roof_insert':plate,'shield_bridge':bridge}.items():
 rows[name]={'bounds_mm':list(s.bounding_box()),'volume_mm3':float(s.volume()),'mass_Al_g_at2p7g_cm3':float(s.volume())*.0027,'hits':{n:a.overlap(s,p) for n,p in parts.items() if a.overlap(s,p)>.005},'RF_keepout_overlap_mm3':a.overlap(s,rf)}
# Roof overlap is exact material replaced by this candidate. It is not an
# exception in the current enclosure audit. Any other hit stays explicit.
for q in rows.values():q['existing_parts_requiring_redesign']=[n for n in q['hits']]
Rleg=.0053/(150*2*.0012*.010)+.003/(150*.014*.010)+.0006/(150*.012*.010)
Rpad=[t/(6*.012*.010) for t in [.0005,.0013]]
out={'status':'UNAPPLIED dimensioned engineering concept, not print/fabrication release','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'current_placement_sha256':hashlib.sha256((E/'placement-source.json').read_bytes()).hexdigest(),'geometry':rows,'process':'Aluminum sheet/formed or machined saddle; replace specified roof region with captured gasketed metal insert. Attachment/frame not yet detailed.','thermal_budget':{'metal_conductivity_min_W_mK':150,'pad_conductivity_target_W_mK':6,'pad_effective_thickness_mm':[.5,1.3],'shield_contact_area_mm2':120,'two_bridge_legs_R_K_W':Rleg,'pad_R_K_W':Rpad,'plate_spreading_acceptance_K_W':.6,'interfaces_acceptance_K_W':.4,'shield_to_external_insert_R_K_W':[Rleg+x+1 for x in Rpad],'target_measured_R_K_W':5},'battery_isolation':'Bridge and insert remain above PCB. No metal link to pack or wrist floor; existing pack/PCB air separation and bottom foam retained. No unverified insulating-film credit.','claim_limits':['Effective5K/W here is MCU-shield-to-metal-insert, not the five-node model electronics-mean-to-whole-shell path.','Package-to-shield heat transfer and other IC heat extraction need measured partitioning.','Only the metal insert is approximately spread; remaining nylon top/sides remain separate thermal regions.','Current lid must be redesigned around gasket/fasteners/capture. This check identifies replaced material rather than ignoring overlaps.','Source-side pad pressure/height must be set from measured shield height with enclosure-supported stops; no compression load on small ICs.']}
(H/'heatpath-candidate.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
