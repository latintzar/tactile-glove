# V4 cuff enclosure and hand-IMU housing

The current CAD uses the actual 100 × 80 × 1.6 mm cuff placement and the routed
16 × 16 × 0.8 mm hand tile. The rigid cuff body is **112 × 104 × 45.5 mm**.
The flat TPU/textile carrier extends 1.6 mm below the body, giving **47.1 mm**
total CAD height before textile. The flat overlap window adds1.6mm at the front, so the complete rigid optical assembly is112×105.6×45.5mm. The previous curved mount gave 53.5 mm. This is
a large cuff; [compact-size-options.md](compact-size-options.md) explains the
50.8 × 38.1 mm target and the measured size limits.

`clearance-report.json` records the current geometry result and physical release
checks. `independent-stl-audit.json` reloads the emitted STL files and independently
checks closed surfaces, connected parts, contact attachment, component collisions
and every manufactured pair. `print-manifest.json` distinguishes manufactured
parts from inspection envelopes. Camera, battery, PCB and NTC envelopes are
reference models. The polycarbonate camera window is a manufactured part.

The current volume-based cuff mechanical budget is approximately **74.18 g**:
PA12 density 1.01 g/cm³, TPU allowance 1.20 g/cm³, optical PC 1.20 g/cm³ and foam
allowance 0.30 g/cm³. Exact per-part volumes and densities are in the report.
Adding the 100 g battery, approximately 24 g PCB and 20–35 g electronics/fastener
allowance gives approximately **218–233 g before external textile and harness**.
This calculation uses solid geometry; a slicer infill multiplier is not applied.

## Geometry and interfaces

- Main PCB bottom Z29.0, top Z30.6. Four edge ledges touch the underside. The lid
  captures four 0.8 mm foam pads in a nominal 0.5 mm gap; the modeled 0.3 mm
  compression is bounded explicitly. Existing board edges carry the clamp loads.
- PA12 shell walls, floor and lid panel 1.3 mm. Local thicker collars
  support glands, the gasket, fasteners and button. Hollow screw columns have
  2.8 mm powder-cleanout ports. The flat 1.6 mm TPU carrier includes strap loops
  and four captured mushroom posts through the floor.
- Five front finger glands, one right hand-IMU gland and one left palm gland have
  stepped retention seats. Cast the glands intact, then knife-cut from bore to insertion edge with zero
  material removal; the assembled CAD represents closed slit faces. Seven internal blanking plugs close unused bores. USB and SD
  have removable service caps. Cable bundle sleeves are formed to 4.0 mm OD for
  the 3.8 mm nominal gland bores; inspect actual compression after harness build.
- A continuous 0.8 mm closed-cell silicone gasket occupies a 0.6 mm lid seat.
  The exact 0.2 mm compression region is audited. The component collision audit
  contains no blanket grommet/base exclusions. Rear lid screws at (24,86) and
  (36,86) clear the mated battery plug, wire return and SD service area. Polymer
  ribs stiffen the left/rear panel; the longest adjacent screw chord is113.2mm.
  A supplier-approved flatness/compression fixture must establish the full
  perimeter0.60±0.05mm gap; the nominal model does not prove seal-load uniformity.
- J14 is at (90, 23.95), facing −Y; J15 is at (81, 14). These changes prevent the
  camera from intersecting the main board or the hand-IMU connector.
- The camera is Camthink 73.002.000035: 8.5 × 8.5 mm face, 6.6 ± 0.2 mm optical
  depth. Its lens faces −Y. The 38.5 mm flat length is exactly 8.5 mm head +
  26 mm neck + 4 mm tail. A 19.7168147 mm straight neck and R4 quarter bend use
  exactly 26 mm. The tail has its contacts toward −Z in the bottom-contact FH12.
  The rear carrier includes an R3.9 inner bend guide, cradle liner and four front
  corner shims; two screws retain the rear plate. Revised Ø7.6 mm lugs, 5.3 mm nut insertion
  slots and straight driver channels provide actual assembly access.
- FH12 drawing EDC3-150229-11 supplies the 0.55 mm contact-bottom reference and
  4.4 mm insertion reference. The 0.3 mm tail center is Z31.3. These reference
  dimensions establish the nominal CAD; incoming camera/connector measurements
  are used for the carrier shims before window bonding.
- A conservative circular 120° cone starts at the complete 5.96 mm lens face.
  It clears the opaque parts. The flat-window tolerance stack includes camera
  depth, printed/finished land, adhesive, sheet, die-cut and registration limits.
  Remaining minimum radial margins are0.487mm at the tape opening,1.082mm at
  the PCedge and0.184mm in the optical tunnel. Incoming camera/flex inspection
  and fitting of the carrier shims remain assembly acceptance steps.
- The RGB light pipe begins above the real 1.6 × 1.6 × 0.9 mm maximum LED and
  bends to the lid face at (60, 76), away from the button diaphragm.
- The hand-tile housing has a removable retained cover, four sewing holes,
  split cable exit and a raised arrow. Align the arrow distally along the third
  metacarpal, stitch the flanges to the textile, and secure a cable strain-relief
  loop toward the wrist. The +140 mm X translation in the CAD is a drawing layout
  offset. Its seven real component envelopes are separately checked.

## Button, materials and fabrication

The C&K PTS636 SK43 SMTR LFS actuator is 4.3 ± 0.2 mm high with 0.30 ± 0.10 mm
travel. The button has a captured floating tip, an internally preloaded spring,
a 0.8 mm rigid stop, a separately assembled cap and a bonded diaphragm. Its
released gap is set to 0.05–0.25 mm against the measured mounted switch.

The selected spring is **SDP/SI S78CSYM030035008**, catalog Type302 stainless,
3mm OD,8mm free length,2.8mm solid length and1.26N/mm nominal rate, squared and
ground ends. [button-spring-specification.md](button-spring-specification.md)
specifies receiving force/rate checks and the factory gap/stop settings. First
article overload/cycle testing uses the4.69N worst accepted contact force.

Quote the rigid shell, lid and camera retainer in natural-gray JLC PA12-HP MJF.
Their broad faces are 1.3 mm; local camera lug/guide details require the supplier
to accept the process-specific geometry. The button has 1.0 mm retaining ledges
and 0.8 mm diametral sliding clearances. Its small-part print/sprue and finishing
route needs acceptance; machined PA12 is an alternative requiring a quote. Set
the nose against the actual mounted switch and finish the guide pin to ≤2.05 mm. The light pipe is machined/bent optical polycarbonate. The camera window is a
Ø22±0.2mm disk cut from RS PRO7698720 stock1mm PCsheet, bonded on a flatØ24mm land
using a die-cut3M VHB LSE-060WF ring,OD22/ID17mm. See
[window-fabrication.md](window-fabrication.md) for PA12 surface preparation,
Primer94, land flatness, pressure, registration and cure requirements. The flat carrier is a TPU95A FDM quote candidate. Glands, plugs, service caps,
battery belt and tile housing require a separately accepted cast/precision
elastomer route; JLC's published TPU minimum size and wall limits exclude these
small thin parts as ordinary individual FDM orders. Thin camera shims, PCB pads, battery pads and the perimeter gasket
are cut parts rather than ordinary FDM prints. The camera cradle liner is heat-formed 0.20 mm TPU film with a 0.25 mm rear patch; its STL shows the assembled liner.

The button diaphragm is **platinum-cured VMQ silicone, 40 ± 5 Shore A,
0.60 ± 0.05 mm thickness**, cut to the emitted rounded outline. Minimum elongation
300%, tensile strength 7 MPa and tear strength 20 kN/m are manufacturer acceptance
requirements. Its outer 2 mm flange bonds into the lid rebate; the central region
bonds to the moving cap, leaving approximately 3 mm free span around the cap.

Use **Permabond2050** for the diaphragm and plunger-cap joint. Apply
**Permabond POP only to silicone surfaces**; dry/abrade/clean PA12. The optical
window uses its separately specified acrylic foam tape process.

## Assembly order

1. Inspect print coupons, plunger fit, hole diameters and gasket seats. Finish
   the nut slots and powder-cleanout ports. Verify each exported part is present.
2. Bond and cure the window and light pipe. Insert camera lug nuts from below,
   fit the liner, shims and camera head, then fit the rear retainer using two
   M2 × 6 low-head screws. Use the verified straight Ø3 mm driver paths while
   the battery and main PCB are still outside the base.
3. Fit the flat carrier posts and 1.7 mm battery foam pads. Wrap the nominal
   69 × 38 × 20 mm pack in insulating foam shims to the 72 × 39 × 21 mm assembly
   envelope. Slide the retaining belt over the padded assembly, seat it and tape
   the insulated NTC to its upper-face pocket, clear of the belt.
4. Seat the main PCB on its edge ledges. Insert the FPC fully and close the FH12
   latch. Dress the direct Micro-Fit battery leads and PH NTC leads and the mated GH/SH harnesses. Fit the
   split glands around sleeved bundles; use the blanking plugs for unused ports.
5. Insert the button tip and selected catalog spring through the plunger's open top; bond
   the separate cap with its spring guide pin. Set the nose length against the
   actual switch, verify released continuity and operation before the hard stop,
   then bond the diaphragm to the cap and lid rebate.
6. Fit four M2 ISO4032 nuts into the base bosses, the PCB clamp pads and perimeter
   gasket. Close with four M2 × 8 ISO14580 low-head screws. Target even gasket
   compression; use a torque coupon to qualify the selected PA12 process.
7. Insert the hand tile, connect its harness, close its TPU cover and stitch the
   sewing flanges to the glove. Thread 24 mm webbing through the flat carrier loops.

## Verification and manufacturing release

```sh
PYTHONPATH=/tmp/glove-engineering/caddeps python3 hardware/glove-v4/enclosure/generate_enclosure.py
PYTHONPATH=/tmp/glove-engineering/caddeps:/tmp/glove-engineering/auditdeps python3 hardware/glove-v4/enclosure/verify_enclosure.py
```

The independent audit covers the actual 48 STL files, 861 manufactured pairs
and 23,562 main-component/part comparisons. The generator additionally checks
17 cap positions, 324 fitted-tip tolerance poses including0.85mm maximum accepted cap stroke, the camera/PCB/FPC interfaces,
120° cone, metal/RF exclusion and fastener fit. The module's own antenna is the
only RF-envelope exemption. The export `component-envelopes.json` contains the
exact audited solids used by the viewer.

The process state is **first_article_fabrication_ready: false**. Obtain the
listed print-and-finish, small elastomer, optical-part and button process quotes;
qualify the selected wire OD/static bend radius; and establish the measured seal
and PCB-pad compression plan. These are explicit process items, separate from
physical testing after a first article exists. Critical finished fits include
window landflatness≤0.20mm, disk/ring registration≤0.30mm, gasket gap0.60±0.05mm,
button released gap0.05–0.25mm and cap stroke0.80±0.05mm. Nominal MJF tolerance
requires local measurement and finishing for these assembly fits.

The independent audit also checks actual harness service volumes, nut insertion
paths and Ø3 mm camera/lid screwdriver access. A wired port replaces only its own
blanking plug. PH/GH routing reservesR2.5mm; supplier wire bend acceptance and
full harness lead dressing remain process work. The battery connector uses
direct AWG22-compatible Micro-Fit contacts, with the selected header placed
within the manufacturer's edge-distance limit. The direct variant uses the original pack leads; a separately identified factory extension variant adds35mm AWG22 per lead with5mm overlap, giving30mm effective reach gain per lead. Its exactR4 paths pass through two staggeredØ4×16mm insulated-joint envelopes. Worst external route74.174mm leaves3.576mm margin after conservative connector consumption and3mm slack with the shortest65mm stock leads. See[battery-connector-fit.md](battery-connector-fit.md).

Physical acceptance remains subject to: supplied component-height and camera-tail inspection;
first-article PCB pad compression; switch force/return/cycle tests; cable pull
and strap-retention tests; window/diaphragm/gland dust-and-splash tests; panel/drop
and temperature testing; and finished-system mass/fit measurement. All545 former generic package heights are now documented manufacturer maxima
plus a separate0.20mm assembly allowance. [height-evidence/README.md](height-evidence/README.md)
links the94 selected-MPN records, primary source locations and evidence hashes.
The new fuse uses2.94mm manufacturer maximum plus0.20mm assembly allowance.

## Primary evidence

- [Camthink camera specification and outline](https://wiki.camthink.ai/docs/neoeyes-ne101-series/ne100-mb01-development-board/hardware-guide/components-overview/), captured in `../interfaces/sources/ov5640-outline-browser.png`.
- Hirose drawing `../interfaces/sources/fh12-family-engineering-drawing.pdf`, page 1 detail a; family catalog alongside it.
- C&K PTS636 drawing `../../glove-v3/component-evidence/interfaces/pts636-datasheet.pdf`.
- Kingbright `../interfaces/sources/kingbright-aptf1616-rgb.pdf`.
- [HP PA12 manufacturer datasheet](https://hp3dprint.eu/downloads/HPPA12Datasheet.pdf), part density 1.01 g/cm³.
- [Permabond silicone preparation](https://permabond.com/materials_bonded/how-to-bond-silicone/) and [2050 technical datasheet](https://permabond.com/wp-content/uploads/2016/04/2050_TDS.pdf).
