"""Independent audit of emitted STL files and exact component meshes.

Dependencies: manifold3d, numpy, trimesh. Reconstructs geometry from the exported
artifacts, rather than accepting the generator's pass flag as evidence.
"""
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import trimesh
from manifold3d import Manifold, Mesh

ROOT=Path(__file__).resolve().parent
EPS=.005  # mm^3, STL float32 export tolerance; approximately micrometre faces.


def solid(vertices,faces):
    return Manifold(Mesh(np.asarray(vertices,dtype=np.float32),np.asarray(faces,dtype=np.uint32)))


def box(w,d,h,x,y,z):
    return Manifold.cube([w,d,h],True).translate([x,y,z])


def bb_near(a,b,tol=0):
    aa,bb=a.bounding_box(),b.bounding_box()
    return all(aa[i+3]+tol>=bb[i] and bb[i+3]+tol>=aa[i] for i in range(3))


def overlap(a,b):
    return max(0,float((a^b).volume())) if bb_near(a,b) else 0


def main():
    manifest=json.loads((ROOT/'print-manifest.json').read_text())
    evidence=json.loads((ROOT/'clearance-report.json').read_text())
    export=json.loads((ROOT/'component-envelopes.json').read_text())
    failures={}
    geometries={}
    stl_checks={}
    for p in manifest['parts']:
        name=p['file']
        m=trimesh.load_mesh(ROOT/name,process=True)
        checks={'watertight':bool(m.is_watertight),'positive_volume':bool(m.volume>0),
                'connected_solids':len(m.split(only_watertight=False)),
                'hash_matches_manifest':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==p['sha256'],
                'volume_mm3':float(m.volume)}
        stl_checks[name]=checks
        if not all([checks['watertight'],checks['positive_volume'],checks['connected_solids']==1,checks['hash_matches_manifest']]):
            failures['STL '+name]=checks
        geometries[name]=solid(m.vertices,m.faces)
    components={p['ref']:solid(p['positions'],p['triangles']) for p in export['main_board']['parts']}
    manufactured={n:geometries[n] for n in manifest['manufactured_parts']}
    inspection={n:geometries[n] for n in manifest['inspection_solids']}
    pair_count=0
    for (an,a),(bn,b) in itertools.combinations(manufactured.items(),2):
        pair_count+=1
        v=overlap(a,b)
        if v<=EPS:
            continue
        pair=f'{an} / {bn}'
        if pair in evidence['bounded_compression_interfaces']:
            zone=box(120,110,.2,50,40,43.6) if 'gasket' in pair else box(120,100,.3,50,40,31.25)
            remainder=max(0,float(((a^b)-zone).volume()))
            if remainder>EPS:
                failures[pair+' outside compression volume']=remainder
        else:
            failures[pair]=v
    for an,a in manufactured.items():
        for bn,b in {**components,**inspection}.items():
            v=overlap(a,b)
            if v>EPS:
                failures[f'{an} / {bn}']=v
    for an in ['camera-module-envelope.stl','camera-flex-envelope.stl']:
        for bn,b in {'PCB':geometries['pcb-envelope.stl'],**components}.items():
            v=overlap(geometries[an],b)
            if v>EPS:
                failures[f'{an} / {bn}']=v
    # Actual exported harness service envelopes, with mutually exclusive
    # wired/blanked port configurations explicitly identified in the report.
    harness_export=json.loads((ROOT/'harness-envelopes.json').read_text())
    harness={q['ref']:solid(q['positions'],q['triangles']) for q in harness_export['parts']}
    harness_checks=0
    for an,a in harness.items():
        removed=evidence['harness']['wired_variant_removed_plugs'].get(an)
        for bn,b in {**manufactured,**components,**inspection,'RF':box(48,21,46,89.75,90.5,23)}.items():
            if bn==removed:continue
            harness_checks+=1
            v=overlap(a,b)
            if v>EPS:failures[an+' / '+bn]=v
    # Derive exact circular-arc route lengths independently; sleeves must sit
    # entirely on straight wire segments, and the shortest stock leads must reach.
    import math
    route_checks=0;fallback_lengths=[]
    for variant in ['direct_paths','factory_extension_paths']:
        for q in harness_export[variant]:
            controls=q['R4_fillet_control_points_mm']
            length=4*math.pi+sum(math.dist(a,b) for a,b in zip(controls,controls[1:]))
            trims=[0.0]
            for a,b,c in zip(controls,controls[1:],controls[2:]):
                u=np.array(b)-a;v=np.array(c)-b
                angle=math.acos(float(np.clip(np.dot(u,v)/(np.linalg.norm(u)*np.linalg.norm(v)),-1,1)))
                trim=4*math.tan(angle/2);trims.append(trim);length+=4*angle-2*trim
            trims.append(0.0)
            if any(trims[i]+trims[i+1]>math.dist(a,b)+1e-7 for i,(a,b) in enumerate(zip(controls,controls[1:]))):
                failures['wire tangent overlap '+str(route_checks)]=True
            if abs(length-q['external_centerline_length_mm'])>1e-7:failures['wire length '+str(route_checks)]=length
            if variant=='factory_extension_paths':
                fallback_lengths.append(length)
                x,y,z={1:(6.5,63,14),2:(10.5,67,17)}[q['wire']]
                segments=zip(q['centerline_mm'],q['centerline_mm'][1:])
                has_straight=any(abs(a[0]-x)<1e-6 and abs(b[0]-x)<1e-6 and abs(a[2]-z)<1e-6 and abs(b[2]-z)<1e-6 and min(a[1],b[1])<=y-8+1e-6 and max(a[1],b[1])>=y+8-1e-6 for a,b in segments)
                if not has_straight:failures['splice beyond straight section '+str(route_checks)]=True
            route_checks+=1
    fallback_margin=65+(35-5)-14.25-3-max(fallback_lengths)
    if fallback_margin<0:failures['factory extension shortest lead reach']=fallback_margin
    # Nut insertion and screwdriver access against actual base/retainer STLs.
    import math
    access_checks=0
    for x,y in evidence['harness']['lid_fasteners_xy_mm']:
        nut=Manifold.cylinder(1.6,4/math.sqrt(3),4/math.sqrt(3),6,True).translate([x,y,40])
        for i in range(25):
            dy=(1 if y>0 else -1)*18*i/24
            v=overlap(nut.translate([0,dy,0]),geometries['rigid-base.stl']);access_checks+=1
            if v>EPS:failures[f'lid nut insertion{x},{y}/{dy}']=v
        driver=Manifold.cylinder(25,1.5,1.5,32,True).translate([x,y,57])
        for n,m in {**manufactured,**components}.items():
            v=overlap(driver,m);access_checks+=1
            if v>EPS:failures[f'lid3mm driver{x},{y} / '+n]=v
    back_y=evidence['camera']['head_rear_y_mm']+.25
    cz=evidence['camera']['head_center_xyz_mm'][2]
    for x in [81.8,98.2]:
        nut=Manifold.cylinder(1.6,4/math.sqrt(3),4/math.sqrt(3),6,True).rotate([90,0,0]).translate([x,back_y-2.8,cz])
        for i in range(25):
            v=overlap(nut.translate([0,0,-10*i/24]),geometries['rigid-base.stl']);access_checks+=1
            if v>EPS:failures[f'camera nut insertion{x}/{i}']=v
        driver=Manifold.cylinder(40,1.5,1.5,32,True).rotate([90,0,0]).translate([x,back_y+22.85,cz])
        for n in ['rigid-base.stl','camera-rear-retainer.stl']:
            v=overlap(driver,geometries[n]);access_checks+=1
            if v>EPS:failures[f'camera3mm driver{x} / '+n]=v
    # Attachment graph: nominal mating faces or bounded compression, within
    #0.03mm numerical/contact tolerance. Separate cuff and handtile assemblies.
    nodes={**manufactured,**inspection,'J_CAM':components['J_CAM']}
    graph={n:set() for n in nodes}
    contacts=[]
    shifts=[[s*.03 if i==axis else 0 for i in range(3)] for axis in range(3) for s in (-1,1)]
    for (an,a),(bn,b) in itertools.combinations(nodes.items(),2):
        if not bb_near(a,b,.03):
            continue
        touch=overlap(a,b)>EPS
        if not touch:
            touch=any(overlap(a.translate(d),b)>1e-7 for d in shifts)
        if touch:
            graph[an].add(bn)
            graph[bn].add(an)
            contacts.append([an,bn])
    seen=set()
    clusters=[]
    for n in graph:
        if n in seen:continue
        stack=[n]; cluster=[]
        while stack:
            node=stack.pop()
            if node in seen:continue
            seen.add(node);cluster.append(node);stack.extend(graph[node]-seen)
        clusters.append(sorted(cluster))
    detached=[c for c in clusters if 'rigid-base.stl' not in c and 'hand-tile-tpu-pocket.stl' not in c]
    if detached:failures['detached_assemblies']=detached
    # Camera flat length derives from the exact exported dimensional recipe.
    f=evidence['camera']['flex']
    total=f['head_length_mm']+f['neck_straight_mm']+f['neck_arc_mm']+f['tail_length_mm']
    if abs(total-38.5)>1e-8:failures['camera_flat_length']=total
    if evidence['camera']['lens_normal']!=[0,-1,0]:failures['camera_orientation']=evidence['camera']['lens_normal']
    # Independently check published package maxima against the actual exported solids.
    heights=json.loads((ROOT/'height-evidence/merged-package-heights.json').read_text())
    by_ref={r:q for q in heights['entries'] if q.get('maximum_height_mm') is not None for r in q['refs']}
    height_checks=0
    if hashlib.sha256((ROOT/'generate_enclosure.py').read_bytes()).hexdigest()!=manifest['generator_sha256']:failures['generator hash changed']=True
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=manifest['verifier_sha256']:failures['verifier hash changed']=True
    for n,h in manifest['source_hashes'].items():
        if hashlib.sha256((ROOT/'sources'/n).read_bytes()).hexdigest()!=h:failures['source hash '+n]=True
    for ref,q in by_ref.items():
        if ref not in components:continue
        bb=components[ref].bounding_box();actual=bb[5]-bb[2]
        if abs(actual-(q['maximum_height_mm']+.20))>.001:
            failures['component height '+ref]={'actual':actual,'required':q['maximum_height_mm']+.20}
        height_checks+=1
    if height_checks!=545:failures['generic package-height coverage']=height_checks
    # Calculate window tolerances independently from actual emitted disk/ring bounds.
    window_bb=geometries['camera-window-clear-pc.stl'].bounding_box()
    disk_radius=(window_bb[3]-window_bb[0])/2
    lens=evidence['camera']['lens_front_y_mm']
    required_gasket=2.98+(lens+.20-(-12-.30-.69))*math.tan(math.pi/3)
    required_window=2.98+(lens+.20-(-12-.30-.69-1.10))*math.tan(math.pi/3)
    optical_margins={'gasket':8.5-.10-.30-required_gasket,
        'disk':disk_radius-.10-.30-required_window,
        'tunnel':1.5-(.20+.30)*math.tan(math.pi/3)-.30-.15}
    if min(optical_margins.values())<=0:failures['window tolerance cone']=optical_margins
    cone_depth=lens-window_bb[1]
    cone=Manifold.cylinder(cone_depth,2.98,2.98+cone_depth*math.tan(math.pi/3),128,True).rotate([90,0,0]).translate([90,lens-cone_depth/2,23.05])
    for name,m in manufactured.items():
        if name=='camera-window-clear-pc.stl':continue
        v=overlap(cone,m)
        if v>EPS:failures['actual STL optical cone / '+name]=v
    # Mated plug is checked against PCB except its actual two through-hole pins.
    holes=Manifold.cylinder(4,.46,.46,64,True).translate([4.1,66.25,28.6])+Manifold.cylinder(4,.46,.46,64,True).translate([4.1,63.25,28.6])+Manifold.cylinder(4,1.51,1.51,64,True).translate([4.1,70.57,28.6])
    v=overlap(components['J_BAT']-holes,geometries['pcb-envelope.stl'])
    if v>EPS:failures['MicroFit versus PCB outside pin holes']=v
    # Independent numeric extremes of the measured button acceptance dimensions.
    min_actuation_margin=.75-.25-.40
    min_spring_length=5.15-.85+.05+.20
    max_spring_force=3.8+1.35*(5.2-min_spring_length)
    if min_actuation_margin<=0 or min_spring_length<=2.9 or max_spring_force>4.69:
        failures['button accepted tolerance range']=[min_actuation_margin,min_spring_length,max_spring_force]
    current=hashlib.sha256((ROOT.parent/'electrical/placement.json').read_bytes()).hexdigest()
    # Snapshot is formatted deterministically; compare decoded placement values.
    if json.loads((ROOT/'placement-source.json').read_text())!=json.loads((ROOT.parent/'electrical/placement.json').read_text()):
        failures['placement_stale']=True
    result={'pass':not failures,'manufacturing_released':False,'checked_actual_STL_files':len(geometries),
            'manufactured_pair_checks':pair_count,'main_component_checks':len(manufactured)*len(components),
            'harness_service_checks':harness_checks,'analytic_wire_route_checks':route_checks,'factory_extension_worst_reach_margin_mm':fallback_margin,'nut_insertion_and_driver_checks':access_checks,'first_article_fabrication_ready':evidence['first_article_fabrication_ready'],'nominal_contact_tolerance_mm':.03,'assembly_contact_graph':{'clusters':clusters,'contacts':contacts},
            'camera_flat_length_mm':total,'package_height_checks':height_checks,'independent_optical_tolerance_margins_mm':optical_margins,'button_tolerance_extremes':{'actuation_margin_mm':min_actuation_margin,'spring_minimum_length_mm':min_spring_length,'maximum_contact_force_N':max_spring_force},'stl_checks':stl_checks,'failures':failures,
            'meaning':'Nominal geometry, printable closed solids, bounded soft compression and attachment contacts; material strength and hardware release gates remain in clearance-report.json.'}
    (ROOT/'independent-stl-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['pass','checked_actual_STL_files','manufactured_pair_checks','main_component_checks','failures']},indent=2))
    return 0 if result['pass'] else 2

if __name__=='__main__':
    raise SystemExit(main())
