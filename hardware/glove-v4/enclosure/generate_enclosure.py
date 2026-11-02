"""Dimensioned V4 mechanical candidate and exhaustive assembly interference audit.

Run: PYTHONPATH=/tmp/glove-engineering/caddeps python3 generate_enclosure.py
The generated report deliberately separates nominal geometry from release gates.
Supplier drawing references and assembly instructions are in README.md.
"""
import hashlib
import itertools
import json
import math
import struct
from pathlib import Path
from manifold3d import Manifold

ROOT = Path(__file__).resolve().parent
PLACEMENT_CANON = ROOT.parent / 'electrical/placement.json'
PLACEMENT_SNAPSHOT = ROOT / 'placement-source.json'
EPS = 1e-5
HEIGHT_EVIDENCE = json.loads((ROOT/'height-evidence/merged-package-heights.json').read_text())
HEIGHT_BY_REF = {ref:entry for entry in HEIGHT_EVIDENCE['entries'] if entry['status']=='manufacturer_maximum_verified' for ref in entry['refs']}
MOUNTING_ALLOWANCE_MM = .20  # Engineering assembly acceptance limit; separate from manufacturer maximum.



def box(w, d, h, x, y, z):
    return Manifold.cube([w, d, h], True).translate([x, y, z])


def cyl(r, h, x, y, z, n=64):
    return Manifold.cylinder(h, r, r, n, True).translate([x, y, z])


def ycyl(r, h, x, y, z, n=64):
    return Manifold.cylinder(h, r, r, n, True).rotate([90, 0, 0]).translate([x, y, z])


def xcyl(r, h, x, y, z, n=64):
    return Manifold.cylinder(h, r, r, n, True).rotate([0, 90, 0]).translate([x, y, z])


def rounded(w, d, h, x, y, z, r=3):
    r = min(r, w/2-.001, d/2-.001)
    s = box(w-2*r, d, h, x, y, z) + box(w, d-2*r, h, x, y, z)
    for sx, sy in itertools.product((-1, 1), repeat=2):
        s += cyl(r, h, x+sx*(w/2-r), y+sy*(d/2-r), z)
    return s


def vol(a, b):
    return max(0.0, float((a ^ b).volume()))


def bounds(m):
    return [float(q) for q in m.bounding_box()]


def disjoint_bbox(a, b):
    aa, bb = bounds(a), bounds(b)
    return any(aa[i+3] <= bb[i] or bb[i+3] <= aa[i] for i in range(3))


def interference(a, b):
    return 0.0 if disjoint_bbox(a, b) else vol(a, b)


def write_stl(m, path):
    mesh = m.to_mesh()
    vp, tris = mesh.vert_properties, mesh.tri_verts
    with path.open('wb') as f:
        f.write(b'Glove V4 dimensioned mechanical candidate'.ljust(80, b' '))
        f.write(struct.pack('<I', len(tris)))
        for tri in tris:
            p = [vp[int(i)] for i in tri]
            a = [p[1][k]-p[0][k] for k in range(3)]
            b = [p[2][k]-p[0][k] for k in range(3)]
            n = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
            norm = math.sqrt(sum(v*v for v in n)) or 1
            f.write(struct.pack('<3f', *[v/norm for v in n]))
            for q in p:
                f.write(struct.pack('<3f', *q[:3]))
            f.write(struct.pack('<H', 0))


def component(q):
    x0, y0, x1, y1 = q['body_bbox_mm']
    ref = q['ref']
    specific = {'J_CAM': 2.2, 'J_SD': 1.68, 'J_USB': 3.26,
                'SW_USER': 4.5, 'D_RGB': .9, 'U_MCU': 3.35,
                'J_IMU_CUFF': 3.0, 'J_BAT': 9.47, 'J_NTC': 9.8, 'F_BAT':3.14}
    verified_h = HEIGHT_BY_REF[ref]['maximum_height_mm']+MOUNTING_ALLOWANCE_MM if ref in HEIGHT_BY_REF else 3.0
    h = specific.get(ref, 7.3 if ref in ['J_THUMB', 'J_INDEX', 'J_MIDDLE', 'J_RING', 'J_LITTLE', 'J_PALM_HEEL'] else verified_h)
    if ref == 'F_BAT':
        h = 2.94+MOUNTING_ALLOWANCE_MM

    if ref == 'J_BAT':
        # Header9.27max+0.20assembly; actual plug and PCB-edge restriction
        # use the manufacturer drawing chain, not the nominal product attribute.
        header=box(x1-x0,y1-y0,9.47,(x0+x1)/2,(y0+y1)/2,30.6+9.47/2)
        # Conservative mated profile; rear82.82±.83drawings±.20assembly.
        plug=box(4.61,83.85-y1,11.26,4.1,(83.85+y1)/2,30.6+11.26/2)
        # Lower rear skirt is bounded outside PCB by note7's edge restriction.
        skirt=box(4.61,83.85-80.55,2,4.1,(83.85+80.55)/2,29.6)
        pins=cyl(.45,3.63,4.1,q['y_mm'],28.785)+cyl(.45,3.63,4.1,q['y_mm']-3,28.785)
        peg=cyl(1.5,3.63,4.1,q['y_mm']+4.32,28.785)
        return header+plug+skirt+pins+peg,h
    if ref == 'U_MCU':
        x0, y0, x1, y1 = 80.65, 60.40, 98.85, 86.10
    if ref == 'D_RGB':
        x0, y0, x1, y1 = 63.7, 75.2, 65.3, 76.8
    # SWITCH body and actuator are separate; bounding box to full actuator
    # height incorrectly fills the air around the narrow actuator.
    if ref == 'SW_USER':
        return (box(6.4, 3.9, 2.5, 72, 76, 31.85) +
                cyl(1.15, 1.8, 72, 76, 34.0)), h
    z = 30.6+h/2 if q['side'] == 'F' else 29-h/2
    return box(x1-x0, y1-y0, h, (x0+x1)/2, (y0+y1)/2, z), h


def quarter_flex(x, y_start, z_start, straight, r=4, width=7, t=.2):
    """Exact annular quarter cylinder, extruded across X; no polyline length fudge."""
    cy, cz = y_start-straight, z_start-r
    annulus = xcyl(r+t/2, width, x, cy, cz, 256) - xcyl(r-t/2, width+1, x, cy, cz, 256)
    quadrant = box(width+2, r+t+1, r+t+1, x, cy-(r+t+1)/2, cz+(r+t+1)/2)
    arc = annulus ^ quadrant
    # Straight meets the annulus at the exact tangent plane.
    return box(width, straight, t, x, y_start-straight/2, z_start) + arc


def front_gland(x, z=39.5, w=10, h=8):
    # Stepped flanges occupy real recessed wall seats. No overlap exclusions.
    neck = box(w, 1.0, h, x, -10.9, z)
    front = box(w+2, .6, h+1, x, -11.7, z-.5)
    rear = box(w+2, .6, h+1, x, -10.1, z-.5)
    seat = neck + front + rear
    hole = ycyl(1.9, 3, x, -10.9, z)
    slit = box(.45, 3, 4.0, x, -10.9, z+2)
    return seat-hole, seat  # Cast intact, then knife-split with zero material removal; assembled split is closed.


def side_transform(m, side, y):
    # Source gland has front normal -Y and centre x0,y-10.9.
    # Left normal -X; right normal +X. Target wall centres ±104.9/-4.9.
    a = 90 if side == 'right' else -90
    tx = 94 if side == 'right' else 6
    return m.rotate([0, 0, a]).translate([tx, y, 0])


def tube(points, radius):
    """Swept routing allowance; spherical joins retain the full cable radius."""
    result=Manifold()
    for a,b in zip(points,points[1:]):
        v=[b[i]-a[i] for i in range(3)]
        length=math.sqrt(sum(x*x for x in v))
        pitch=math.degrees(math.acos(v[2]/length))
        yaw=math.degrees(math.atan2(v[1],v[0]))
        result+=Manifold.cylinder(length,radius,radius,24,True).rotate([0,pitch,yaw]).translate([(a[i]+b[i])/2 for i in range(3)])
    for a in points:
        result+=Manifold.sphere(radius,24).translate(a)
    return result


def fillet_path(points,radius):
    """Exact circular fillets in each 3D corner plane; reject insufficient runs."""
    def sub(a,b):return [x-y for x,y in zip(a,b)]
    def add(a,b):return [x+y for x,y in zip(a,b)]
    def mul(a,s):return [x*s for x in a]
    def norm(a):return math.sqrt(sum(x*x for x in a))
    out=[points[0]]
    tangent_lengths=[0.0]
    for prev,p,nxt in zip(points,points[1:],points[2:]):
        aa,bb=sub(p,prev),sub(nxt,p);la,lb=norm(aa),norm(bb)
        u,v=mul(aa,1/la),mul(bb,1/lb);co=max(-1,min(1,sum(a*b for a,b in zip(u,v))))
        theta=math.acos(co)
        if theta<1e-6:
            tangent_lengths.append(0.0);out.append(p);continue
        d=radius*math.tan(theta/2)
        tangent_lengths.append(d)
        start=add(p,mul(u,-d));normal=mul(sub(v,mul(u,co)),1/math.sin(theta));center=add(start,mul(normal,radius))
        out.append(start)
        for i in range(1,17):
            t=theta*i/16;out.append(add(center,add(mul(normal,-radius*math.cos(t)),mul(u,radius*math.sin(t)))))
    tangent_lengths.append(0.0)
    for i,(a,b) in enumerate(zip(points,points[1:])):
        if tangent_lengths[i]+tangent_lengths[i+1]>math.dist(a,b)+1e-7:
            raise ValueError(("Overlapping R4 fillet tangents",i,tangent_lengths[i],tangent_lengths[i+1],math.dist(a,b)))
    out.append(points[-1]);return out


def fillet_length(points,radius):
    length=sum(math.dist(a,b) for a,b in zip(points,points[1:]))
    for a,b,c in zip(points,points[1:],points[2:]):
        u=[b[i]-a[i] for i in range(3)];v=[c[i]-b[i] for i in range(3)]
        co=sum(x*y for x,y in zip(u,v))/math.sqrt(sum(x*x for x in u)*sum(x*x for x in v))
        theta=math.acos(max(-1,min(1,co)))
        length+=radius*theta-2*radius*math.tan(theta/2)
    return length


def main():
    placement = json.loads(PLACEMENT_CANON.read_text())
    PLACEMENT_SNAPSHOT.write_text(json.dumps(placement, indent=2)+'\n')
    assert placement['board_mm'] == [100.0, 80.0, 1.6]
    pq = {q['ref']: q for q in placement['parts']}
    assert abs(pq['J_BAT']['x_mm']-4.1)<1e-4 and abs(pq['J_BAT']['y_mm']-66.25)<1e-4, 'Recalculate Micro-Fit mating transform after placement change'
    board = box(100, 80, 1.6, 50, 40, 29.8)
    battery = box(72, 39, 21, 48, 39.5, 13.5)
    ntc = box(8, 4, 2, 28, 23, 25)
    rf = box(48, 21, 46, 89.75, 90.5, 23)
    outer = rounded(112, 104, 43.5, 50, 40, 21.75, 10)
    base = outer - rounded(109.4,101.4,44,50,40,23.3,8.7)
    #1.3mm PA12 walls and floor; thicker gasket seat only at top.
    base += rounded(112,104,1.6,50,40,42.7,10)-rounded(107.6,99.6,2,50,40,42.7,7.8)
    lid = rounded(112,104,1.3,50,40,44.85,10)
    lid += rounded(112,104,.8,50,40,43.9,10)-rounded(109,101,1,50,40,43.9,8.5)
    manufactured, inspection, metals = {}, {}, {}
    fit_interfaces = []

    # Actual board contact at Z29; split top pads retain the board at Z30.6.
    supports = [(0, 23), (18, 80), (100, 12), (100, 43)]
    for i, (x, y) in enumerate(supports):
        angle=-90 if y==80 else (180 if x==100 else 0)
        def support_transform(m):
            return m.rotate([0,0,angle]).translate([x,y,0])
        base += support_transform(box(5.3,5,27.85,-1.15,0,15.075))
        lid += support_transform(box(5.0,5,13.2,-1.15,0,37.7))
        pad = support_transform(box(2.3,5,.8,-.35,0,31.0))
        manufactured[f'pcb-clamp-pad-{i+1}.stl'] = pad
        fit_interfaces += [{'a':'rigid-base.stl','b':'PCB','surface':f'pad {i+1} at Z29','nominal_gap_mm':0},
                           {'a':f'pcb-clamp-pad-{i+1}.stl','b':'PCB','surface':'Z30.6','nominal_gap_mm':0},
                           {'a':'rigid-lid.stl','b':f'pcb-clamp-pad-{i+1}.stl','surface':'Z31.1 bonded pad','nominal_gap_mm':0}]
        base += support_transform(box(.6,5,1.6,-.3,0,29.8))

    # ISO M2 nuts in side-loaded pockets, M2x8 low-head screws. The lid and
    # bosses meet at Z43.5, rather than floating above each other.
    fasteners = [(-2, -6), (102, -6), (24, 86), (36, 86)]
    nut_pockets, screw_clearances = [], []
    for x, y in fasteners:
        base += cyl(3.5,42.3,x,y,22.35)
        lid += cyl(3.5,.8,x,y,43.9)
        hole = cyl(1.2, 10, x, y, 40)
        nut = cyl(2.65, 2.2, x, y, 40, 6).rotate([0, 0, 0])
        access = box(5.3, 8, 2.2, x, y+(-4 if y < 0 else 4), 40)
        base -= hole+nut+access
        # Hollow1.3mm-wall column with2.8mm powder-cleanout ports into cavity.
        base -= cyl(2.2,35.5,x,y,19.75)
        for vent_z in (4,35):
            base -= xcyl(1.4,6,x+(3 if x<50 else -3),y,vent_z)
        lid -= cyl(1.2, 4, x, y, 44.5)
        lid -= cyl(2.2, 1.6, x, y, 44.7)
        screw = cyl(1, 8, x, y, 39.9) + cyl(1.9, 1.5, x, y, 44.65)
        nut_actual = cyl(4/math.sqrt(3), 1.6, x, y, 40, 6)-cyl(.8, 2, x, y, 40)
        metals[f'lid-screw-{len(nut_pockets)+1}'] = screw
        metals[f'lid-nut-{len(nut_pockets)+1}'] = nut_actual
        nut_pockets.append(nut)
        screw_clearances.append(hole)

    # Local lid ribs bridge the shifted rear clamps to the left/rear seal.
    # Clip to the existing outer profile; no change to case dimensions.
    rear_left_ribs=box(2.6,33,1.4,-2.2,73.5,43.6)+box(106,2.6,1.4,50,87.5,43.6)
    for x,y in fasteners:
        rear_left_ribs-=cyl(3.6,.6,x,y,43.2)
    lid+=rear_left_ribs ^ rounded(107.6,99.6,2,50,40,43.6,7.8)
    for x,y in fasteners:
        lid-=cyl(1.2,4,x,y,43.5)+cyl(2.2,1.6,x,y,44.7)

    # Seven serviceable, split TPU glands; cap each unused gland from inside.
    glands = [(f'cable-grommet-{i+1}', x, None, 0) for i, x in enumerate([11, 28, 45, 62, 79])]
    glands += [('cable-grommet-6', 0, 'right', 5), ('cable-grommet-7', 0, 'left', 51)]
    for name, x, side, y in glands:
        g, seat = front_gland(x, z=39.5 if side != 'right' else 38.5)
        z = 39.5 if side != 'right' else 38.5
        plug = ycyl(1.9, 2.2, x, -10.9, z) + ycyl(2.8, .8, x, -9.4, z)
        # Each slit runs continuously from the bore to the insertion edge.
        if side:
            g, seat, plug = [side_transform(q, side, y) for q in [g, seat, plug]]
        collar=box(16,2.2,11,x,-10.9,38)
        if side:
            collar=side_transform(collar,side,y)
        base += collar
        seat_shift=[.02,0,0] if side else [0,.02,0]
        base-=seat+seat.translate(seat_shift)+seat.translate([-v for v in seat_shift])
        manufactured[name+'.stl'] = g
        manufactured[name+'-blanking-plug.stl'] = plug
        fit_interfaces.append({'a': 'rigid-base.stl', 'b': name+'.stl', 'surface': 'stepped flange pocket; lid captures upper edge', 'nominal_gap_mm': 0})

    # USB and microSD service caps are installed for the closed assembly.
    usbseat = box(2.2, 13, 8, 104.9, 54, 33.2)
    usbcap = box(2.2, 13, 8, 104.9, 54, 33.2) + box(.8, 15, 10, 103.4, 54, 33.2)
    base += box(2.2,17,12,104.9,54,33.2)
    base -= usbseat
    manufactured['usb-service-cap.stl'] = usbcap
    sdseat = box(24, 2.2, 10, 54, 90.9, 33.5)
    sdcap = sdseat + box(26, .8, 12, 54, 89.4, 33.5)
    base += box(28,2.2,14,54,90.9,33.5)
    base -= sdseat
    manufactured['sd-service-cap.stl'] = sdcap

    # Battery restrained by a closed TPU belt, slipped over cell before seating.
    strap = box(8, 41, 23, 48, 39.5, 13.5)-box(10, 39, 21, 48, 39.5, 13.5)
    base += box(8.2,41.2,.85,48,39.5,1.575)
    manufactured['battery-retaining-belt.stl'] = strap
    foam = box(72,39,1.7,48,39.5,2.15)-box(8.2,42,3,48,39.5,2.1)
    # Two independent foam pads are separate manufactured parts.
    for i, p in enumerate(foam.decompose()):
        manufactured[f'battery-foam-pad-{i+1}.stl'] = p
    for x in (10.9, 85.1):
        base += box(1.5,40.5,4.25,x,39.5,3.275)
    for y in (18.9, 60.1):
        rail = box(73.5,1.5,4.25,48,y,3.275)-box(8.2,4,5,48,y,3.3)
        base += rail

    # Sealed diaphragm. The wide flange is bonded into a lid rebate, and a
    # central region bonds to the moving cap;3mm free span accommodates travel.
    # All solids below are shown in the rest state.
    boot_outer = rounded(20,24,.6,72,76,45.2,3)
    boot_inner = rounded(16,20,.6,72,76,45.2,2.5)
    boot = boot_outer + boot_inner
    lid -= rounded(20.2,24.2,.6,72,76,45.2,3.1)
    lid -= rounded(16,20,3,72,76,44.5,2.5)
    # Central plunger body has a spring cavity, retained sliding tip and roof.
    plunger = cyl(3.5,7.2,72,76,40.3)
    plunger_cap=rounded(10,14,1,72,76,44.4,2.5)+cyl(1.0,4.05,72,76,41.925)
    plunger -= cyl(2.4, 6.2, 72, 76, 40.8)
    plunger -= cyl(1.65, 2, 72, 76, 37.2)
    # A collar rests0.8mm above the rigid annular lower stop. Bonded diaphragm
    # retains the moving body in the upward direction.
    stop_ring = cyl(5.4, 1.5, 72, 76, 41.35)-cyl(3.9, 2.5, 72, 76, 41.35)
    lid += stop_ring
    for xx, bridge_x in [(64.5,66),(79.5,78)]:
        lid += box(2,2,3.1,xx,76,43.05)+box(4,2,1.5,bridge_x,76,41.35)
    for xx in (64.5,79.5):
        lid+=box(1.2,13.8,2.8,xx,82.9,42.9)
    plunger += cyl(5.0,1.0,72,76,43.4)
    plunger -= cyl(2.4,2,72,76,43.4)
    # Tip uses a mechanical flange inside spring chamber; adjustable nose uses
    # measured nose finishing so rest clearance is .15±.10mm at the mounted switch.
    tip = cyl(1.25, 2.65, 72, 76, 36.375)+cyl(2.0, 1.0, 72, 76, 38.2)
    manufactured['button-plunger.stl'] = plunger
    manufactured['button-plunger-cap.stl']=plunger_cap
    manufactured['button-floating-tip.stl'] = tip
    manufactured['button-silicone-diaphragm.stl'] = boot

    # Indicator bends away from the sealed button flange, then terminates in
    # a retained flange below the lid. Optical face is polished clear PC.
    pipe_low = cyl(1.15, 4, 64.5, 76, 33.6)
    angle = math.degrees(math.atan2(4.5, 7.4))
    length = math.hypot(4.5, 7.4)
    pipe_mid = Manifold.cylinder(length, 1.15, 1.15, 48, True).rotate([0, -angle, 0]).translate([62.25, 76, 39.3])
    pipe = pipe_low+pipe_mid+cyl(1.15, 2.5, 60, 76, 44.25)+cyl(2, .6, 60, 76, 43.2)
    lid += cyl(2.2,.8,60,76,43.9)
    lid -= cyl(1.35,4,60,76,44.5)
    manufactured['rgb-lightpipe.stl'] = pipe

    # Camera route from primary drawings. Tail contacts face -Z in the
    # bottom-contact FH12; the untwisted down-bend turns lens normal to -Y.
    cam = pq['J_CAM']
    mouth = cam['body_bbox_mm'][1]
    tip_y, flex_z = mouth+4.4, 30.6+.55+.15
    tail_start = tip_y-4
    straight = 26-4*math.pi/2
    rear_y = tail_start-straight-4
    head_top = flex_z-4
    center_z = head_top-4.25
    front_y = rear_y-6.6
    head = box(8.5, 6.6, 8.5, 90, rear_y-3.3, center_z)
    flex = quarter_flex(90, tail_start, flex_z, straight)
    flex += box(12.5, 4, .3, 90, tip_y-2, flex_z)
    # Physical connector body is an envelope; subtract only the real mating
    # FPC slot from J_CAM, never its entire overlap with arbitrary geometry.
    fh12_slot = box(12.7, 4.4, .34, 90, mouth+2.2, flex_z)
    # Flat overlap window: stock1mm PC disk and0.6mm VHB LSE foam ring.
    # The broad bond land takes ordinary flat finishing, without radial fitting.
    window_y = -13.1
    window = ycyl(11, 1.0, 90, window_y, center_z)
    window_bond = ycyl(11,.6,90,-12.3,center_z)-ycyl(8.5,1,90,-12.3,center_z)
    base += ycyl(12,2.5,90,-10.75,center_z)
    window_seat = Manifold()
    tunnel_start, tunnel_end = front_y+.3, -13.0
    tunnel_depth=tunnel_start-tunnel_end
    lens_aperture=Manifold.cylinder(tunnel_depth,2.98-.3*math.tan(math.pi/3)+1.5,
                                    2.98+(front_y-tunnel_end)*math.tan(math.pi/3)+1.5,128,True).rotate([90,0,0]).translate([90,(tunnel_start+tunnel_end)/2,center_z])
    camera_clearance = box(8.9, 7.3, 8.9, 90, rear_y-3.2, center_z)
    base -= camera_clearance+window_seat+lens_aperture
    # Bottom and side cradle surfaces support the head, with0.2mm service
    # clearance. Thin factory shims establish the exact optical datum.
    cradle = box(11.3, 7.1, 11.3, 90, rear_y-3.3, center_z)-camera_clearance
    cradle -= box(7.4, 8, 3, 90, rear_y-3.2, head_top+1)
    cradle -= lens_aperture+window_seat
    base += cradle
    # Rear plate and two M2 retention bolts trap the module at its back and
    # lateral carrier ears. Plate is installed before the main PCB.
    back_y = rear_y+.25
    backplate = box(25,1.3,10.9,90,back_y+.65,center_z)
    backplate -= box(7.4, 2, 8, 90, back_y+.5, head_top+3.1)
    for xx in (81.8, 98.2):
        lug = ycyl(3.8, 5, xx, back_y-2.5, center_z)
        base += lug-camera_clearance
        base -= ycyl(1.2, 8, xx, back_y-2, center_z)
        # M2 nyloc-less hex nut accessible from underside of the lug.
        pocket = Manifold.cylinder(2.2, 2.65, 2.65, 6, True).rotate([90, 0, 0]).translate([xx, back_y-2.8, center_z])
        base -= pocket+box(5.3, 2.2, 16, xx, back_y-2.8, center_z-7.5)
        backplate -= ycyl(1.2, 3, xx, back_y+.5, center_z)
        metals[f'camera-screw-{xx}']=ycyl(1,6,xx,back_y-1.7,center_z)+ycyl(1.9,1.55,xx,back_y+2.075,center_z)
        metals[f'camera-nut-{xx}']=ycyl(4/math.sqrt(3),1.6,xx,back_y-2.8,center_z,6)-ycyl(.8,2,xx,back_y-2.8,center_z)
        # Straight3.6mm driver access through the nearby PCB support, before battery/PCB installation.
        base-=ycyl(1.8,40,xx,back_y+22.9,center_z)
    # Integrated R3.9 inner guide supports the R4 centreline bend. Its rear
    #edge is trimmed0.15mm ahead of the PCB; lateral strips join the retainer.
    bend_y=tail_start-straight
    bend_former=xcyl(3.9,8.2,90,bend_y,head_top,256)^box(10,4.5,4.2,90,-2.4,head_top+2.1)
    base-=bend_former+bend_former.translate([0,0,.05])+bend_former.translate([0,0,-.05])
    backplate+=bend_former
    liner=box(8.9,6.6,.2,90,rear_y-3.3,center_z-4.35)
    for xx in (85.65,94.35):
        liner+=box(.2,6.6,8.5,xx,rear_y-3.3,center_z)
    liner+=box(8.9,.25,8.7,90,rear_y+.125,center_z-.1)
    manufactured['camera-tpu-cradle-liner.stl']=liner
    for i,(sx,sz) in enumerate(itertools.product((-1,1),repeat=2)):
        manufactured[f'camera-front-shim-{i+1}.stl']=box(1, .25,1,90+sx*3.7,front_y-.125,center_z+sz*3.7)
    base-=box(25.6,1.3,11.5,90,back_y+.65,center_z)  # Retainer pocket; front plane retains lug bearing faces.
    manufactured['camera-rear-retainer.stl'] = backplate
    manufactured['camera-window-clear-pc.stl'] = window
    manufactured['camera-window-adhesive-ring.stl'] = window_bond

    # Wrist saddle and strap loops form one connected TPU print. Four mushroom
    # posts pass through floor holes; retaining heads seat on the floor top.
    # Flat carrier:1.6mm TPU95A rails and strap loops; no curved saddle.
    # This is an attachment frame, with textile providing the skin-contact pad.
    saddle=box(76,4,1.6,50,14,-.8)+box(76,4,1.6,50,66,-.8)
    for xx in (35,65):
        saddle+=box(4,100,1.6,xx,40,-.8)
    for yy in (-7,87):
        saddle+=rounded(34,10,1.6,50,yy,-.8,3)-rounded(24,4,3,50,yy,-.8,1.5)
    for x,y in [(18,14),(82,14),(18,66),(82,66)]:
        saddle+=cyl(3.2,1.6,x,y,-.8)
        saddle+=cyl(2,2.3,x,y,1.05)+cyl(3.2,1,x,y,2.7)
        base+=cyl(3.6,1.05,x,y,1.675)
        base-=cyl(2.1,3,x,y,1.1)
    manufactured['flat-tpu-textile-carrier.stl'] = saddle
    # Continuous0.8mm closed-cell gasket, compressed to0.6mm by the lid.
    # Its exact0.2mm compression zone is the only permitted interference.
    gasket = rounded(111,103,.8,50,40,43.3,9.5)-rounded(108.8,100.8,2,50,40,43.3,8.4)
    gasket_groove = rounded(111,103,.6,50,40,43.2,9.5)-rounded(108.8,100.8,2,50,40,43.2,8.4)
    base -= gasket_groove
    for name in list(manufactured):
        if name.startswith('cable-grommet-') and 'blanking' not in name:
            manufactured[name] -= gasket_groove
    manufactured['lid-perimeter-gasket.stl'] = gasket
    compression_zone = gasket ^ box(120,110,.2,50,40,43.6)

    # Separate hand IMU housing. Translation+140X is a drawing layout datum,
    # not a claimed position on the glove. PCB datumZ1.0, component side+Z.
    tile_board = box(16,16,.8,148,8,1.4)
    tile_base = rounded(20,20,6,148,8,3,2)-box(16.3,16.3,6,148,8,4)
    tile_base -= box(16.95,16.95,.5,148,8,5.55)
    tile_cap = rounded(20,20,1,148,8,6.5,2)
    skirt = box(16.2,16.2,.8,148,8,5.9)-box(14.2,14.2,1,148,8,5.9)
    bead = box(16.9,16.9,.5,148,8,5.55)-box(14.2,14.2,1,148,8,5.55)
    tile_cap += skirt+bead
    for xx in (135.5,160.5):
        flange=rounded(6,20,1.5,xx,8,.75,2)
        for yy in (2,14):
            flange-=cyl(.8,3,xx,yy,.75)
        tile_base+=flange
    tile_base += ycyl(2.7,3,148,18.5,3.3)
    tile_base -= ycyl(1.3,9,148,18,3.3)+box(.5,9,3,148,18,4.9)
    arrow=cyl(2.5,.4,0,0,0,3).rotate([0,0,-90]).translate([148,5,7.2])
    tile_cap += arrow+box(1.2,5,.4,148,8,7.2)
    manufactured['hand-tile-tpu-pocket.stl']=tile_base
    manufactured['hand-tile-tpu-cover.stl']=tile_cap
    tile_placement=json.loads((ROOT/'hand-tile-placement-source.json').read_text())
    tile_components={}
    for q in tile_placement['parts']:
        x0,y0,x1,y1=q['body_bbox_mm']
        h={'J1':3.0,'U1':1.06,'C1':1.10,'C2':1.10,'C3':1.10,'R1':.75,'R2':.75}[q['ref']]  # Same selected MPN maxima+0.20mm as main board; JST SH stays specific.
        tile_components[q['ref']]=box(x1-x0,y1-y0,h,140+(x0+x1)/2,(y0+y1)/2,1.8+h/2)
    tile_reference_hits={}
    for n,m in [('hand-tile-tpu-pocket.stl',tile_base),('hand-tile-tpu-cover.stl',tile_cap)]:
        for ref,rm in {'PCB':tile_board,**tile_components}.items():
            v=interference(m,rm)
            if v>EPS:
                tile_reference_hits[f'{n} / {ref}']=v
    manufactured['rigid-base.stl'] = base
    manufactured['rigid-lid.stl'] = lid
    inspection = {'camera-module-envelope.stl': head, 'camera-flex-envelope.stl': flex,
                  'battery-envelope.stl': battery, 'battery-ntc-envelope.stl': ntc,
                  'pcb-envelope.stl': board, 'hand-tile-pcb-envelope.stl':tile_board}

    # Remove sub-micrometre Boolean edges before float32 STL serialization.
    # This preserves dimensions while preventing coincident zero-volume faces.
    manufactured={n:m.simplify(.0001) for n,m in manufactured.items()}
    base,lid=manufactured['rigid-base.stl'],manufactured['rigid-lid.stl']
    envelopes = {q['ref']: component(q)[0] for q in placement['parts']}
    envelopes['J_CAM'] -= fh12_slot
    def export_envelope(ref,m):
        mesh=m.to_mesh()
        return {'ref':ref,'bounds_mm':bounds(m),'positions':[list(map(float,v[:3])) for v in mesh.vert_properties],
                'triangles':[list(map(int,t)) for t in mesh.tri_verts],
                'height_evidence':({'mpn':HEIGHT_BY_REF[ref]['mpn'],'manufacturer_maximum_mm':HEIGHT_BY_REF[ref]['maximum_height_mm'],'assembly_allowance_mm':MOUNTING_ALLOWANCE_MM,'audited_height_mm':HEIGHT_BY_REF[ref]['maximum_height_mm']+MOUNTING_ALLOWANCE_MM} if ref in HEIGHT_BY_REF else {'basis':'specific dimensional envelope'})}
    component_export={'units':'mm','main_board':{'parts':[export_envelope(n,m) for n,m in envelopes.items()]},
                      'hand_tile':{'drawing_offset_mm':[140,0,0],'parts':[export_envelope(n,m) for n,m in tile_components.items()]},
                      'envelope_note':'Exact audited solids. All545 former generic package heights use documented manufacturer maxima plus a separate0.20mm assembly allowance. SW_USER is nominal4.3mm with lot-adjusted button tip and a fullheight/travel sweep. J_CAM contains its actual FPC slot.'}
    (ROOT/'component-envelopes.json').write_text(json.dumps(component_export,separators=(',',':'))+'\n')
    # Explicit wire service paths. These are reserved harness volumes, not
    # assertions about an unspecified wire supplier's minimum bend radius.
    # PH:2 individual wires OD<=1.5mm,R2.5; GH:OD<=0.7mm,R2.5 before bundling.
    harness={}
    for ref in ['J_NTC']:
        q=pq[ref]
        wires=Manifold()
        for dx in [0,2]:
            x,y=q['x_mm']+dx,q['y_mm']
            pts=[[x+2.5*(1-math.cos(t)),y,40.4+2.5*math.sin(t)] for t in [i*math.pi/32 for i in range(17)]]
            pts.append([x+8,y,42.9])
            wires+=tube(pts,.75)
        harness[ref+'_wire_bends']=wires^box(120,110,10,50,40,45.4)
    # Bound all undimensioned wire-exit heights, with OD1.85 plus0.10mm
    # radial routing allowance. R4 half-turn passes around the left PCB edge.
    # Each emitted path is real geometry; this is a service-envelope family,
    # not a guessed single centerline from a drawing without the Z datum.
    battery_paths=[]
    route_families=[]
    battery_wires=Manifold()
    for exit_z in [31.525+i*(40.935-31.525)/48 for i in range(49)]:
        for pack_y in [49,51]:
            arc=[[4.1-.7*4*(1-math.cos(t)),83.85+4*math.sin(t),exit_z-math.sqrt(.51)*4*(1-math.cos(t))] for t in [i*math.pi/64 for i in range(65)]]
            controls=[arc[-1],[-1.5,79,exit_z-math.sqrt(.51)*8],[-1.5,62,18],[5.8,pack_y,13.5],[10.875,pack_y,13.5]]
            rest=fillet_path(controls,4)
            pts=arc+rest[1:]
            battery_paths.append({'exit_z_mm':exit_z,'pack_exit_y_mm':pack_y,'external_centerline_length_mm':math.pi*4+fillet_length(controls,4),'R4_fillet_control_points_mm':controls})
            route_families.append(pts)
    # Convex hull each short segment across every family sample. An extra
    #0.20mm axis allowance bounds between-sample variation; cube sections
    # conservatively contain the circular1.85mm wire envelope. This avoids
    # thousands of overlapping tube Booleans while preserving the same routes.
    for i in range(len(route_families[0])-1):
        cloud=[]
        for path in route_families:
            for point in path[i:i+2]:
                for delta in itertools.product([-1.125,1.125],repeat=3):
                    cloud.append([point[k]+delta[k] for k in range(3)])
        battery_wires+=Manifold.hull_points(cloud)
    # The path starts at the rear mating plane. Trim only the terminal portion
    # already contained by the exact named connector envelope.
    harness['J_BAT_wire_service_family']=battery_wires-envelopes['J_BAT']
    # Factory-only alternative when measured stock-lead reach is insufficient.
    # Same AWG22 and Micro-Fit contacts; the two splice sleeves are staggered.
    harness['J_BAT_extension_splices']=ycyl(2,16,6.5,63,14)+ycyl(2,16,10.5,67,17)
    fallback_paths=[]
    for wire_id,(level,x,turn_y) in enumerate([(14,6.5,49),(17,10.5,55)],1):
        family=[]
        for exit_z in [31.525+i*(40.935-31.525)/48 for i in range(49)]:
            for pack_y in [49,51]:
                arc=[[4.1-.7*4*(1-math.cos(t)),83.85+4*math.sin(t),exit_z-math.sqrt(.51)*4*(1-math.cos(t))] for t in [i*math.pi/64 for i in range(65)]]
                turn_rear_y=77.2 if wire_id==1 else 79.6
                controls=[arc[-1],[-1.5,turn_rear_y,exit_z-math.sqrt(.51)*8],[-1.5,turn_rear_y,level],[x,turn_rear_y,level],[x,pack_y if wire_id==1 else turn_y,level],[10.875,pack_y,13.5]]
                rest=fillet_path(controls,4)
                pts=arc+rest[1:];family.append(pts)
                fallback_paths.append({'wire':wire_id,'exit_z_mm':exit_z,'pack_exit_y_mm':pack_y,'external_centerline_length_mm':math.pi*4+fillet_length(controls,4),'R4_fillet_control_points_mm':controls,'centerline_mm':pts})
        envelope=Manifold()
        for i in range(len(family[0])-1):
            cloud=[[point[k]+delta[k] for k in range(3)] for path in family for point in path[i:i+2] for delta in itertools.product([-1.125,1.125],repeat=3)]
            envelope+=Manifold.hull_points(cloud)
        harness[f'J_BAT_factory_extension_wire_{wire_id}']=envelope-envelopes['J_BAT']


    for ref,x in [('J_INDEX',11),('J_MIDDLE',28),('J_RING',45),('J_LITTLE',62),('J_THUMB',79)]:
        q=pq[ref]; count=int(q['footprint'].split('_1x')[1].split('-')[0].split('_')[0])
        wires=Manifold()
        for i in range(count):
            sx=x+(i-(count-1)/2)*1.25
            pts=[[sx,4.5-2.5*(1-math.cos(t)),37.9+2.5*math.sin(t)] for t in [j*math.pi/32 for j in range(17)]]
            angle=2*math.pi*i/count
            pts.extend([[sx,-3,40.4],[x+1.1*math.cos(angle),-9.5,39.5+1.1*math.sin(angle)]])
            wires+=tube(pts,.35)
        harness[ref+'_wire_bends']=wires^box(120,110,10,50,40,42.9)
    # Palm wires fan above their connector before heading to the left gland.
    wires=Manifold()
    for i in range(14):
        sx=12.5+(i-6.5)*1.25
        pts=[[sx-2.5*(1-math.cos(t)),51,37.9+2.5*math.sin(t)] for t in [j*math.pi/32 for j in range(17)]]
        angle=2*math.pi*i/14
        pts.extend([[0,51,40.4],[-3.5,51+1.1*math.cos(angle),39.5+1.1*math.sin(angle)]])
        wires+=tube(pts,.35)
    harness['J_PALM_HEEL_wire_bends']=wires^box(120,110,10,50,40,42.9)
    harness['J_IMU_CUFF_wire_bends']=tube([[81,14,34.2],[81,14,36],[88,14,37.5],[95,5,38.5],[102.5,5,38.5]],.6)
    (ROOT/'harness-envelopes.json').write_text(json.dumps({'units':'mm','parts':[export_envelope(n,m) for n,m in harness.items()],'factory_extension_paths':fallback_paths,'direct_paths':battery_paths,
        'status':'Reserved service bends; supplier wire OD and static bend-radius acceptance remain an explicit process item; full interconnect lead dressing remains assembly validation.'},separators=(',',':'))+'\n')
    wired_port_plugs={ref+'_wire_bends':f'cable-grommet-{i}-blanking-plug.stl' for ref,i in [('J_INDEX',1),('J_MIDDLE',2),('J_RING',3),('J_LITTLE',4),('J_THUMB',5),('J_IMU_CUFF',6),('J_PALM_HEEL',7)]}
    harness_hits={}
    for an,am in harness.items():
        for bn,bm in {**manufactured,**envelopes,**inspection,'RF_conductive_exclusion':rf}.items():
            if bn==wired_port_plugs.get(an):continue  # Wired assembly replaces only this port's blanking plug.
            v=interference(am,bm)
            if v>EPS:harness_hits[an+' / '+bn]=v
    # Nominal actuator envelope is paired with the nominal manufactured tip;
    # every specified switchheight/travel extreme is tested with its fitted nose.
    pair_hits, comp_hits, reference_hits = {}, {}, {}
    compression_interfaces={}
    for (an, am), (bn, bm) in itertools.combinations(manufactured.items(), 2):
        v = interference(am, bm)
        if v > EPS:
            if set([an,bn])==set(['lid-perimeter-gasket.stl','rigid-lid.stl']):
                permitted=vol(am ^ bm, compression_zone)
                compression_interfaces[f'{an} / {bn}']={'actual_overlap_mm3':v,'bounded_compression_overlap_mm3':permitted,'compression_mm':.2,'free_thickness_mm':.8,'installed_thickness_mm':.6}
                if v-permitted>EPS:
                    pair_hits[f'{an} / {bn} outside compression zone']=v-permitted
            elif (an.startswith('pcb-clamp-pad-') and bn=='rigid-lid.stl') or (bn.startswith('pcb-clamp-pad-') and an=='rigid-lid.stl'):
                region=box(120,100,.3,50,40,31.25)
                permitted=vol(am ^ bm,region)
                compression_interfaces[f'{an} / {bn}']={'actual_overlap_mm3':v,'bounded_compression_overlap_mm3':permitted,'compression_mm':.3,'free_thickness_mm':.8,'installed_thickness_mm':.5}
                if v-permitted>EPS:
                    pair_hits[f'{an} / {bn} outside compression zone']=v-permitted
            else:
                pair_hits[f'{an} / {bn}'] = v
    for an, am in manufactured.items():
        for bn, bm in envelopes.items():
            v = interference(am, bm)
            if v > EPS:
                comp_hits[f'{an} / {bn}'] = v
        for bn, bm in inspection.items():
            v = interference(am, bm)
            if v > EPS:
                reference_hits[f'{an} / {bn}'] = v
    other_camera_hits = {}
    for an in ['camera-module-envelope.stl', 'camera-flex-envelope.stl']:
        for bn, bm in {'PCB': board, **envelopes}.items():
            v = interference(inspection[an], bm)
            if v > EPS:
                other_camera_hits[f'{an} / {bn}'] = v

    # Conservative120-degree circular cone starts at full5.96mm lens face.
    cone_depth = max(.01, front_y+13.6)
    cone = Manifold.cylinder(cone_depth, 2.98, 2.98+cone_depth*math.tan(math.pi/3), 128, True).rotate([90, 0, 0]).translate([90, front_y-cone_depth/2, center_z])
    optical_hits = {}
    for an, am in manufactured.items():
        if an == 'camera-window-clear-pc.stl':
            continue  # transparent optical material, still collision-tested above
        v = interference(cone, am)
        if v > EPS:
            optical_hits[an] = v
    # Conservative tolerance stack: finished land Y±.30, camera depth±.20,
    # tape0.6±15%, sheet1.0±.10 receiving limit, radial registration±.30,
    # die-cut diameters±.20. Both opaque tape opening and PC edge are checked.
    gasket_worst_front=-12-.30-.69
    window_worst_front=gasket_worst_front-1.10
    gasket_required_radius=2.98+(front_y+.20-gasket_worst_front)*math.tan(math.pi/3)
    window_required_radius=2.98+(front_y+.20-window_worst_front)*math.tan(math.pi/3)
    gasket_available_radius=8.5-.10-.30
    window_available_radius=11-.10-.30
    optical_margin=min(gasket_available_radius-gasket_required_radius,window_available_radius-window_required_radius,1.5-(.20+.30)*math.tan(math.pi/3)-.30-.15)
    window_tolerance={'disk_MPN':'RS PRO7698720','disk_diameter_mm':22,'disk_diameter_tolerance_mm':.2,'sheet_thickness_mm':1.0,'sheet_receiving_thickness_mm':[.9,1.1],
        'bond_MPN':'3M VHB LSE-060WF','bond_thickness_mm':.6,'bond_thickness_tolerance_percent':15,'bond_ring_OD_ID_mm':[22,17],
        'bond_land_diameter_mm':24,'finished_land_flatness_mm_max':.2,'land_y_mm':-12,'land_y_tolerance_mm':.3,
        'radial_registration_mm_max':.3,'lens_depth_tolerance_mm':.2,'gasket_clearance_margin_mm':gasket_available_radius-gasket_required_radius,'tunnel_radial_extra_mm':1.5,'tunnel_diameter_tolerance_mm':.3,'carrier_to_land_axial_tolerance_mm':.3,'tunnel_clearance_margin_mm':1.5-(.20+.30)*math.tan(math.pi/3)-.30-.15,
        'window_edge_clearance_margin_mm':window_available_radius-window_required_radius,'nominal_front_projection_mm':1.6,
        'maximum_front_projection_with_tolerances_mm':2.09,
        'surface_process':'Dry/depowder PA12; locally flatten bond land; clean; two thin coats3M Primer94 with full drying between coats; bond at21–38C with100kPa ring pressure;72hour dwell. Coupon adhesion and splash acceptance qualify actual MJF surface.'}

    rf_hits = {n: interference(rf, m) for n, m in {**envelopes, **metals, 'battery': battery}.items()}
    rf_hits = {n: v for n, v in rf_hits.items() if v > EPS and n != 'U_MCU'}
    rf_antenna = interference(rf, envelopes['U_MCU'])
    fastener_hits = {}
    for n, m in metals.items():
        for pn in ['rigid-base.stl', 'rigid-lid.stl', 'camera-rear-retainer.stl']:
            v = interference(m, manufactured[pn])
            if v > EPS:
                fastener_hits[f'{n} / {pn}'] = v
    sweep_hits = {}
    for displacement in [i*.05 for i in range(17)]:
        p = (plunger+plunger_cap).translate([0,0,-displacement])
        for n, m in {**envelopes, **{n:m for n,m in manufactured.items() if n not in ['button-plunger.stl','button-plunger-cap.stl','button-floating-tip.stl','button-silicone-diaphragm.stl']}}.items():
            v = interference(p, m)
            if v > EPS:
                sweep_hits[f'{displacement:.2f}mm / {n}'] = v
    tolerance_tip_hits={}
    tip_cases=[]
    for actual_h,actual_travel,gap in itertools.product([4.1,4.3,4.5],[.2,.3,.4],[.05,.25]):
        nose=30.6+actual_h+gap
        variant=cyl(1.25,37.7-nose,72,76,(37.7+nose)/2)+cyl(2,1.0,72,76,38.2)
        for d in [i*.05 for i in range(18)]:
            depression=min(actual_travel,max(0,d-gap))
            tip_drop=min(d,gap+actual_travel)
            moving_tip=variant.translate([0,0,-tip_drop])
            moving_body=(plunger+plunger_cap).translate([0,0,-d])
            act_h=actual_h-2.5-depression
            actual_switch=box(6.4,3.9,2.5,72,76,31.85)+cyl(1.15,act_h,72,76,33.1+act_h/2)
            for name,m in [('switch',actual_switch),('plunger',moving_body),('lid',lid)]:
                v=interference(moving_tip,m)
                if v>EPS:
                    tolerance_tip_hits[f'H{actual_h}/T{actual_travel}/gap{gap}/stroke{d:.2f}/{name}']=v
        tip_cases.append({'height_mm':actual_h,'switch_travel_mm':actual_travel,'gap_mm':gap,
                          'actuation_before_stop_margin_mm':.8-gap-actual_travel,
                          'spring_length_at_stop_mm':5.2-.8+gap+actual_travel, 'minimum_spring_length_with_stop_and_installation_tolerances_mm':5.15-.85+gap+actual_travel, 'minimum_actuation_margin_with_stop_tolerance_mm':.75-gap-actual_travel})
    # Selected catalog spring. Receiving checks cover unspecified catalog tolerances.
    button_tolerance = {'switch_height_mm': [4.1, 4.5], 'switch_travel_mm': [.2, .4],
                        'factory_adjusted_rest_gap_mm': [.05, .25], 'cap_travel_mm': .8,'factory_measured_cap_travel_mm':[.75,.85],'factory_measured_installed_spring_length_mm':[5.15,5.25],
                        'required_compliant_tip_travel_mm':.60,'tolerance_cases':tip_cases,'tested_poses':len(tip_cases)*18,
                        'force_note':'Spring preload minimum 3.2 N exceeds datasheet maximumoperatingforce2.94N; maximum accepted contact force including stop/installation tolerances4.69 N requires switch overload validation.',
                        'diaphragm':{'material':'Platinum-cured VMQ silicone','hardness_Shore_A':[35,45],'thickness_mm':.6,'thickness_tolerance_mm':.05,'bond':'Permabond2050; POP primer on silicone only; PA12 dried and abraded','bond_source':'https://permabond.com/materials_bonded/how-to-bond-silicone/'},
                        'spring_requirement': {'OD_mm': 3, 'free_length_mm': 8, 'installed_length_mm': 5.2,
                                               'rate_N_per_mm': [1.15, 1.35], 'preload_N':[3.2,3.8]},
                        'spring_design':'SDP/SI S78CSYM030035008 catalog compression spring; receiving specification in button-spring-specification.md',
                        'catalog_spring':{'MPN':'S78CSYM030035008','manufacturer':'SDP/SI','material':'Type302 stainless','wire_diameter_mm':.35,'OD_mm':3,'free_height_mm':8,'solid_height_mm':2.8,'rate_N_per_mm':1.26,'ends':'squared and ground','catalog_physical_page':64,'catalog_source':'https://www.sdp-si.com/D815/D815-Metric-Section10-Hardware.pdf','nominal_force_at_5_2mm_N':3.528,'nominal_force_at_4_65mm_N':4.221,'receiving_force_at_5_2mm_N':[3.2,3.8],'receiving_rate_N_per_mm':[1.15,1.35],'receiving_force_at_4_65mm_N_max':4.55,'receiving_force_at_4_55mm_N_max':4.69,'receiving_OD_mm_max':3.10,'receiving_solid_height_mm_max':2.90},
                        'commissioning':'Finish tip nose to0.15mm nominal released gap; verify0.05mm minimum and0.25mm maximum with feelers against mounted switch; measure stop0.80±0.05mm and installed spring length5.20±0.05mm; verify released continuity and actuation before hard-stop.'}

    solid_checks = {}
    for n, m in {**manufactured, **inspection}.items():
        mesh = m.to_mesh()
        solid_checks[n] = {'status': str(m.status()), 'connected_solids': len(m.decompose()),
                           'volume_mm3': float(m.volume()), 'bounds_mm': bounds(m),
                           'triangle_count':len(mesh.tri_verts),'pieces':[{'volume_mm3':float(piece.volume()),'bounds_mm':bounds(piece)} for piece in m.decompose()]}
        write_stl(m, ROOT/n)
    geometry_failures = {n: q for n, q in solid_checks.items() if q['connected_solids'] != 1 or not q['status'].endswith('NoError')}
    connector_board_hits={}
    bat_pin_clearance=cyl(.46,4,4.1,66.25,28.6)+cyl(.46,4,4.1,63.25,28.6)+cyl(1.51,4,4.1,70.57,28.6)
    v=interference(envelopes['J_BAT']-bat_pin_clearance,board)
    if v>EPS:connector_board_hits['MicroFit / PCB outside its two pin holes and locating hole']=v
    numeric_failures = {'mated_connector_board_collision':connector_board_hits,'manufactured_pair_collisions': pair_hits, 'manufactured_vs_all_components': comp_hits,
                        'manufactured_vs_reference': reference_hits, 'camera_vs_board_and_components': other_camera_hits,
                        'opaque_optical_cone_hits': optical_hits, 'rf_conductive_hits': rf_hits,
                        'fastener_fit_hits': fastener_hits, 'button_full_sweep_hits': sweep_hits,
                        'wire_service_envelopes':harness_hits,'invalid_or_disconnected_solids': geometry_failures,'hand_tile_fit':tile_reference_hits,'button_tip_tolerance_sweep':tolerance_tip_hits}
    failed_groups = [k for k, v in numeric_failures.items() if v]
    if optical_margin < 0:
        failed_groups.append('window_optical_margin')
    material_rows=[]
    for n,m in manufactured.items():
        if n.startswith(('rigid-','button-plunger','button-floating','camera-rear')):
            material,density='HP MJF PA12',1.01
        elif n in ['rgb-lightpipe.stl','camera-window-clear-pc.stl']:
            material,density='Optical polycarbonate',1.20
        elif 'silicone-diaphragm' in n:
            material,density='Silicone40A sheet,0.6mm',1.10
        elif 'adhesive' in n:
            material,density='3M VHB LSE-060WF acrylic foam',.710
        elif 'foam' in n or 'gasket' in n or 'clamp-pad' in n or 'front-shim' in n:
            material,density='Closed-cell silicone foam (selected-density allowance)',.30
        elif n=='flat-tpu-textile-carrier.stl':
            material,density='TPU95A (density allowance)',1.20
        else:
            material,density='TPU90A cast/precision (density allowance)',1.20
        volume=float(m.volume())/1000
        material_rows.append({'file':n,'material':material,'density_g_cm3':density,'solid_volume_cm3':volume,'mass_g':volume*density})
    cuff_mass=sum(q['mass_g'] for q in material_rows if not q['file'].startswith('hand-tile-'))
    tile_mass=sum(q['mass_g'] for q in material_rows if q['file'].startswith('hand-tile-'))
    mass_budget={'method':'Exact solid mesh volume times material density; excludes any arbitrary infill factor',
                 'density_source_PA12':'https://hp3dprint.eu/downloads/HPPA12Datasheet.pdf',
                 'cuff_manufactured_parts_g':cuff_mass,'hand_tile_housing_g':tile_mass,
                 'battery_g':100,'main_PCB_g':24,'electronics_and_fasteners_allowance_g':[20,35],
                 'estimated_cuff_total_g':[cuff_mass+144,cuff_mass+159],
                 'excluded':'Textile, external wrist strap webbing, tactile sheets and external wire harness; measure completed unit',
                 'parts':material_rows}
    report = {'status': 'PROCESS REVIEW: nominal geometry plus explicit fabrication and acceptance stages', 'units':'mm','case_dimensions_mm':{'width':112,'length':104,'height':45.5},'assembly_envelope_mm':{'width':112,'length_with_window':105.6,'height_with_flat_carrier':47.1,'window_front_projection':1.6},'mass_budget':mass_budget,
              'board': {'size_mm': [100, 80, 1.6], 'bottom_z_mm': 29, 'top_z_mm': 30.6,
                        'contact_supports_xy_mm': supports, 'new_mounting_holes': False},
              'case': {'outer_x_mm': [-6,106], 'outer_y_mm': [-12,92], 'rigid_z_mm': [0,45.5],
                       'wall_mm':1.3,'floor_mm':1.3,'lid_panel_mm':1.3,'lid_rim_mm':2.0},
              'camera': {'source': 'FH12 EDC3-150229-11 detaila; Camthink73.002.000035 outline',
                         'connector_xy_mm': [cam['x_mm'],cam['y_mm']], 'mouth_y_mm': mouth,
                         'insertion_depth_reference_mm': 4.4, 'contact_bottom_above_PCB_mm': .55,
                         'tail_tip_y_mm': tip_y, 'flex_center_z_mm': flex_z,
                         'head_center_xyz_mm': [90,rear_y-3.3,center_z], 'head_xyz_size_mm': [8.5,6.6,8.5],
                         'head_rear_y_mm': rear_y, 'lens_front_y_mm': front_y, 'lens_normal': [0,-1,0],
                         'flex': {'head_length_mm':8.5, 'neck_straight_mm':straight, 'neck_arc_mm':4*math.pi/2,
                                  'bend_radius_centerline_mm':4, 'tail_length_mm':4, 'total_flat_length_mm':38.5,
                                  'neck_width_mm':7, 'neck_thickness_mm':.2,'tail_width_mm':12.5,'tail_thickness_mm':.3,
                                  'twist_deg':0,'contact_normal_at_tail':[0,0,-1]},
                         'optics': {'vendor_diagonal_FOV_deg':120,'tested_circular_FOV_deg':120,
                                    'lens_face_radius_mm':2.98,'opaque_cone_hits_mm3':optical_hits,
                                    'window_clear_radius_mm':8.5,'flat_window':window_tolerance,'bend_inner_guide_radius_mm':3.9,'worst_depth_optical_margin_mm':optical_margin}},
              'button': button_tolerance, 'rf': {'antenna_only_exemption': 'U_MCU module contains its own antenna',
                                               'antenna_reference_overlap_mm3':rf_antenna,'other_conductive_overlap_mm3':rf_hits},
              'package_height_evidence':{'file':'height-evidence/merged-package-heights.json','sha256':hashlib.sha256((ROOT/'height-evidence/merged-package-heights.json').read_bytes()).hexdigest(),'former_generic_instances_resolved':545,'remaining_generic_instances':0,'assembly_allowance_mm':MOUNTING_ALLOWANCE_MM},
              'manufactured_component_test_count':len(manufactured)*len(envelopes),
              'manufactured_pair_test_count':len(manufactured)*(len(manufactured)-1)//2,
              'all_component_count':len(envelopes), 'contact_interfaces':fit_interfaces,
              'blanket_pair_exemptions':[], 'bounded_compression_interfaces':compression_interfaces,
              'hand_tile':{'board_mm':[16,16,.8],'housing_mm':[31,22,7.4],'assembly_drawing_offset_mm':[140,0,0],
                           'component_envelopes_checked':len(tile_components),'marking':'Arrow points distally along third metacarpal',
                           'attachment':'Four1.6mm sewing holes in TPU flanges; stitched to textile; snap-fit removable cover',
                           'cable_exit':'2.6mm split bore; dress cable toward wrist and secure textile strain-relief loop'},
              'numeric_failures':numeric_failures,
              'geometry_pass':not failed_groups, 'failed_groups':failed_groups,'solids':solid_checks,
              'release_gates': ['Inspect SDP/SI S78CSYM030035008 spring against specified5.2mm load and rate; validate released-force and4.69N overload on PTS636SK43 lots; fit captured tip nose to actual switch height.',
                                'Measure supplied camera tail insertion and lens-depth datum against manufacturer reference drawing; fit carrier shims before glue cure.',
                                'Measure assembled component heights against documented package maxima plus0.20mm assembly allowance; confirm actual wire bend/bundle diameters.',
                                'Validate TPU gland compression,25percent lid-gasket compression, bonded button diaphragm and window adhesive with an assembled dust/splash test.',
                                'Verify printed dimensional coupons, PCB thickness clamp compression, strap retention load, thermal behavior and battery assembly on built hardware.'],
              'placement_sha256':hashlib.sha256(PLACEMENT_SNAPSHOT.read_bytes()).hexdigest()}
    unresolved_process=[
        'Obtain an accepted PA12 print-and-finish quote (broad shell faces1.3mm; local1.10mm lug wall/guide features need process-specific acceptance): aligned M2 holes/nut slots, camera datums, window seat and gasket faces need the specified local final dimensions; nominal MJF tolerance alone is insufficient.',
        'Confirm the small button print/sprue and finishing route, or price machined PA12 alternative. Set tip length against measured switch; inspect0.8mm diametral sliding clearances and finish spring-guide pin to<=2.05mm.',
        'Confirm a cast elastomer supplier for small glands/caps/tile parts. JLC FDM95A minimum30x30x15 and1.2mm walls do not cover these small thin features. Knife-split glands after casting with zero material removal.',
        'Confirm selected wire OD and allowed static R2.5mm bends for the PH/GH routing volumes; qualify remaining lead dressing. Battery lead route is bounded across undimensioned exits; direct leads require measured reach after crimp, otherwise use the exactR4 factory extension routes,35mm addedAWG22 per lead/5mm overlap, with assembler-qualified insulated joints and<=2mOhm per splice.',
        'Approve silicone foam grade and a measured compression/flatness plan for lid and PCB pads. Rear screw positions avoid RF and SD; polymer ribs stiffen the rear/left span, but seal-load uniformity across the longest113.2mm screw chord requires fixture/deflection acceptance.0.2mm gasket compression cannot be guaranteed by two as-printed mating faces.',
        'Quote the optical polycarbonate lightpipe and cut stock1mm PC window; prepare the flat PA12 bond land and apply specified3M Primer94/LSE060WF tape process. Full geometry/materials span several fabrication processes.'
    ]
    report.update({'first_article_fabrication_ready':False,'unresolved_design_or_process_items':unresolved_process,
        'physical_acceptance_tests':['Switch return/force/overload/cycle test after measured gap setting','Cable pull and gland/diaphragm/window dust-splash tests','PCB pad compression, strap pull, panel/drop, temperature and completed-system mass/fit measurements'],
        'jlc_process':{'PA12_tolerance_below_100mm_mm':.3,'PA12_tolerance_above_100mm_percent':.4,'case_112mm_span_tolerance_mm':.448,'case_104mm_span_tolerance_mm':.416,'minimum_wall_mm':1.0,'quote_preflight_general_wall_mm_strictly_greater_than':1.2,'broad_shell_wall_selected_mm':1.3,'minimum_escape_hole_mm':2.5,'source':'https://jlc3dp.com/help/article/pa12-hp-nylon'},
        'dfm_revision':{'previous_commit':'5542e9e','rigid_case_dimension_change_mm':[0,0,0],'carrier_below_case_mm':1.6,'previous_saddle_below_case_mm':8,'assembly_height_excluding_textile_mm':47.1,'previous_assembly_height_excluding_textile_mm':53.5,'button_retaining_ledges_mm':1.0,'button_sliding_diametral_clearances_mm':.8,'camera_lug_OD_mm':7.6,'camera_nut_pocket_radial_wall_min_mm':1.10,'nut_insertion_slot_width_mm':5.3,'powder_escape_holes_mm':2.8,'gland_split':'Knife cut after casting, zero material removal; CAD is closed assembled condition'},
        'harness':{'file':'harness-envelopes.json','service_volumes_checked':len(harness),'wired_variant_removed_plugs':wired_port_plugs,'PH_wire_OD_max_mm':1.5,'battery_connector':{'header':'43045-0200','housing':'43025-0200','contact':'43030-0007','pin1_xy_mm':[4.1,66.25],'peg_xy_mm':[4.1,70.57],'PCB_edge_distance_mm':9.43,'manufacturer_edge_distance_max_mm':10.16,'edge_tolerance_allowance_mm':.20,'bare_header_max_height_mm':9.27,'assembly_allowance_mm':.20,'mated_profile_max_height_mm':11.26,'rear_skirt_bound_mm':{'x':[1.795,6.405],'y':[80.55,83.85],'z':[28.6,30.6],'basis':'Conservative rear skirt bound outside PCB from note7; verify supplied housing falls within audited envelope'},'wire_exit_y_nominal_mm':82.82,'wire_exit_y_drawing_tolerance_mm':.83,'wire_exit_y_assembly_allowance_mm':.20,'wire_exit_z_family_mm':[31.525,40.935],'underdetermined_datum':'Wire centerlineZ and pack exitY/Z are bounded service families, not manufacturer dimensions','wire_OD_max_mm':1.85,'routing_axis_allowance_mm':.20,'minimum_reserved_centerline_bend_R_mm':4,'external_path_length_range_mm':[min(q['external_centerline_length_mm'] for q in battery_paths),max(q['external_centerline_length_mm'] for q in battery_paths)],'stock_lead_mm':[65,75],'fallback_minimum_effective_lead_mm':95,'fallback_added_conductor_per_lead_mm':35,'fallback_overlap_per_lead_mm':5,'fallback_effective_gain_per_lead_mm':30,'fallback_total_added_conductor_mm':70,'fallback_splice_count':2,'fallback_max_resistance_per_splice_mOhm':2,'conservative_terminal_consumption_upper_bound_mm':14.25,'strain_relief_slack_mm':3,'fallback_external_path_length_range_mm':[min(q['external_centerline_length_mm'] for q in fallback_paths),max(q['external_centerline_length_mm'] for q in fallback_paths)],'fallback_worst_reach_margin_mm':95-14.25-3-max(q['external_centerline_length_mm'] for q in fallback_paths),'direct_termination_acceptance':'Measured usable lead length after selected contact crimp must exceed measured routed length plus3mm strain-relief slack. Otherwise factory extension variant required.','fallback':'Factory35mm AWG22 added per lead minus5mm overlap gives30mm effective extension; total nominal100mm; same43030-0007 contacts. Exact crimp consumption and pack exit datum remain assembly measurements.'},'battery_splice_envelopes':{'variant':'Factory extension fallback only','insulated_max_OD_mm':4,'insulated_max_length_mm':16,'centers_mm':[[6.5,63,14],[10.5,67,17]]},'GH_wire_OD_max_mm':.7,'reserved_bend_centerline_R_mm':2.5,'lid_fasteners_xy_mm':fasteners,'rear_left_lid_ribs_mm':[2.6,1.3],'rear_left_clamp_span_nominal_mm':math.dist(fasteners[0],fasteners[2]),'adjacent_lid_screw_chords_mm':{'front':math.dist(fasteners[0],fasteners[1]),'left':math.dist(fasteners[0],fasteners[2]),'rear':math.dist(fasteners[2],fasteners[3]),'right':math.dist(fasteners[1],fasteners[3])},'gasket_edge_acceptance':'Measure installed gap0.60±0.05mm along entire perimeter after fasteners tightened; local lid ribs support rear-left seal, print flatness and first-article compression test required','variant_groups':{'direct':['J_BAT_wire_service_family'],'factory_extended':['J_BAT_factory_extension_wire_1','J_BAT_factory_extension_wire_2','J_BAT_extension_splices']},'scope':'Variants are mutually exclusive; worst-clearance service family covers undimensioned exit heights; measured reach and assembler splice process acceptance remain explicit'}})
    (ROOT/'clearance-report.json').write_text(json.dumps(report,indent=2)+'\n')
    manifest = {'status':report['status'],'manufacturing_released':False,'manufactured_parts':list(manufactured),
                'inspection_solids':list(inspection),'parts':[{'file':n,'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),
                                                           **solid_checks[n]} for n in {**manufactured,**inspection}],
                'case_dimensions_mm':report['case_dimensions_mm'],'assembly_envelope_mm':report['assembly_envelope_mm'],'mass_budget':mass_budget,
                'fabrication':{'rigid_parts':'MJF HP PA12; solid-volume mass basis','camera_window_and_lightpipe':'Window:cutØ22±.2mm from RS PRO7698720 stock1mm PCsheet; preserve supplied optical faces. Lightpipe:machined/bent optical PC, polished ends.','button_diaphragm':'Die-cut0.6mm VMQ40A silicone; Permabond2050 plusPOP on silicone only','camera_liner':'Heat-formed0.20mm TPUfilm with0.25mm rear patch; STL shows assembled liner','gasket_and_pads':'Die-cut closed-cell silicone foam to specified free thickness','TPU_parts':'TPU90A precisionSLS/cast, thin-feature coupon required','window_bond':'Die-cut3M VHB LSE-060WF0.6mm ring,OD22/ID17±.2mm; prepared/primed flat PA12land;100kPa applicationpressure and72hourroomtemperaturedwell'},
                'purchased_hardware':{'lid':'4×M2×8 ISO14580 low-head screws,4×M2ISO4032 nuts',
                                      'camera':'2×M2×6 low-head screws,2×M2 nuts',
                                      'button':'SDP/SI S78CSYM030035008 Type302 catalog compression spring,OD3/free8/solid2.8mm/nominalrate1.26Npermm; receiving load/rate checks in button-spring-specification.md',
                                      'diaphragm':'Platinum-cured VMQ silicone40±5ShoreA,0.60±0.05mm; Permabond2050 with POP on silicone surface only'},
                'placement_sha256':report['placement_sha256'],'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'verifier_sha256':hashlib.sha256((ROOT/'verify_enclosure.py').read_bytes()).hexdigest(),'source_hashes':{n:hashlib.sha256((ROOT/'sources'/n).read_bytes()).hexdigest() for n in ['molex-header.pdf','molex-housing.pdf','jauch-250480.pdf','sdp-si-metric-hardware.pdf','rs-pro-7698720-polycarbonate.pdf','3m-window-bond-evidence.txt']}}
    for k in ['first_article_fabrication_ready','unresolved_design_or_process_items','physical_acceptance_tests','jlc_process','dfm_revision','harness']:
        manifest[k]=report[k]
    manifest['fabrication']['button_parts']='PA12 MJF near-net with measured finishing and supplier small-part/sprue acceptance; machined PA12 is an unquoted alternative, not released procurement.'
    manifest['fabrication']['TPU_parts']='Flat carrier:TPU95A FDM candidate at1.6mm wall; small glands/caps/tile parts:separate cast elastomer quote, not ordinary JLC FDM.'
    manifest['fabrication']['critical_fits']='Process acceptance required:window overlap landflatness<=0.2mm and disk/ring registration<=0.3mm; measured0.6+/-0.05mm gasket gap; matched/drilled M2 axes; switch gap0.05..0.25mm set from mounted switch.'
    (ROOT/'print-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    scene=[]
    for n,m in {**manufactured,**inspection}.items():
        mesh=m.to_mesh()
        scene.append({'name':n,'positions':[list(map(float,v[:3])) for v in mesh.vert_properties],
                      'triangles':[list(map(int,t)) for t in mesh.tri_verts]})
    (ROOT/'scene.json').write_text(json.dumps(scene,separators=(',',':')))
    print(json.dumps({'geometry_pass':report['geometry_pass'],'failed_groups':failed_groups,
                      'failure_counts':{k:len(v) for k,v in numeric_failures.items()},
                      'components':len(envelopes),'manufactured_parts':len(manufactured),
                      'camera':report['camera']},indent=2))
    # Keep all evidence available on failure; never claim manufacturing release.
    return 0 if report['geometry_pass'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
