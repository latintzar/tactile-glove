# Eight-layer power and routing audit

Status: engineering checkpoint. `routing-progress.json` and its board hash define the published state. Manufacturing requires zero opens and a final native DRC, together with the checks below. Intermediate calculation results identify their exact board SHA; results for a scratch board do not certify another snapshot.

## Reproduction

Use KiCad7 pcbnew with NumPy, SciPy and Shapely2:

```sh
python3 power-integrity/run_audit.py glove-v4-routing-candidate.kicad_pcb /tmp/glove-power-audit
```

The runner verifies the actual power via arrays and connector position before calculating. It solves the actual filled copper as a two-dimensional resistor sheet at0.10 and0.075mm resolution, adds0.05mm when the change exceeds5%, and records the solver residual. The battery calculation includes entry copper, post-fuse copper, SYS copper, return copper, actual barrel lengths and conservative short surface escapes. Parallel planes and redundant traces are omitted. This is a DC estimate, not physical thermal qualification.

## Stack and fabrication contract

Selected primary vendor template: **JLC081611-3313**, nominal finished1.6mm, template compressed1.636mm. Exact API snapshot and request are in `selected-stackup.json`. Assumed maximum finished thickness1.76mm reflects the1.6mm±10% manufacturing option; the supplier must confirm the final stack.

| Layer | Role | Copper | Dielectric below |
|---|---|---:|---:|
| F.Cu | Signal |35µm|0.092mm3313|
| In1.Cu | GND top |30µm|0.130mmcore|
| In2.Cu | Signal top |30µm|0.406mm7628×2|
| In3.Cu | PowerA |30µm|0.130mmcore|
| In4.Cu | PowerB |30µm|0.406mm7628×2|
| In5.Cu | Signal bottom |30µm|0.130mmcore|
| In6.Cu | GND bottom |30µm|0.092mm3313|
| B.Cu | Signal |35µm|—|

All four signal layers have an adjacent ground plane. The wide power planes replace the six-layer candidate's fragmented main supply: its sampled main-plane resistance was84–90mΩ at30µm/50°C, versus approximately3mΩ for the eight-layer geometry. Each reported value must be refreshed after changes to vias or pours.

The sensitivity calculation assumes24µm inner copper,28µm outer copper,15µm minimum barrel plating and50°C copper. These are engineering lower-bound allocations, not a statement that an advertised average plating thickness guarantees a minimum. Fabricator confirmation is required. The TI SNVA766 long-trace equation uses a10°C rise target and is reported for comparison. Short package escapes and broad perforated planes require thermal qualification; the single widest corridor metric does not account for parallel current paths.

## Vias, pads and stencil

Signal vias use0.45/0.20mm and selected0.40/0.20mm diameter/drill pairs, with0.15mm tracks/clearance and0.25mm hole-to-copper/hole-to-hole project constraints. The0.40/0.20 option has0.10mm annular ring and can incur the vendor's small-via surcharge. Power vias include0.60/0.30mm arrays, two direct regulator-input0.40/0.20mm vias and three PGND0.45/0.20mm vias. Project DRC remains authoritative; no physical errors are waived.

Vias intersecting component lands require filled, planarized and copper-capped via-in-pad processing (VIPPO), including the charger exposed-pad and direct power-pin vias. Tenting is insufficient under soldered lands. This processing must appear in the fabricator/assembler quotation. The BQ RTW footprint has a2.7×2.7mm exposed copper pad and four1.1×1.1mm paste apertures:66.4% nominal paste area. Four exposed-pad vias transfer heat to the ground planes. Final stencil thickness, aperture reductions and allowable voiding require assembly DFM for the mixed WCSP/QFN/passive board.

## Signal return paths and RF

F/In2 reference In1GND; B/In5 reference In6GND. A signal transition between those groups needs a nearby ground stitch joining the reference planes. Camera and USB transition coordinates and distances must be extracted from the final board and checked after the last repair. Added ground stitches must preserve all native clearance rules. USB pair length, coupling, layer transitions and impedance remain a distinct final review; connectivity alone is insufficient. The selected stack is the input to the fabricator's impedance calculation.

The ESP32 module origin remains(89.75,73.25),180°, with the antenna beyond the PCB'sY80 edge. Its manufacturer maximum body reachesY86.10. The antenna exclusion envelope isX65.75..113.75,Y80..101 across all copper layers and through the enclosure's metal/battery volume. Enclosure geometry must preserve that envelope; the module's own antenna is intentional.

## Battery entry and fault coordination

J12 uses Molex43045-0200 with43025-0200 housing and43030-0007 AWG22 contacts. Its origin(4.1,66.25),180° places the locating peg atY70.57,9.43mm from theY80 edge, satisfying the primary drawing's10.16mm maximum with0.73mm nominal margin. Housing mating, latch and wire envelopes are checked independently by enclosure CAD.

F1 is Littelfuse045102.5MRL before every board branch. The protected Jauch250480 pack remains intact. The2.5A fuse is a fault device, not a2.5A current clamp: the primary data specify opening within5s at5A. Molex's6A AWG22/two-circuit wire-to-board reference is based on30°C temperature rise. Parent power/battery_path_checks.py owns the full190mΩ harness/contact/fuse/BATFET/copper allocation and thermal derating. The PCB allocation is15mΩ and must be met by the full battery-plus-return calculation, rather than by the main3.3V plane alone.

Primary sources: [JLC copper weight](https://jlcpcb.com/help/article/jlcpcb-copper-weight), [JLC multilayer stacks](https://jlcpcb.com/help/article/multi-layer-pcb-standard-laminated-structures), [JLC capabilities](https://jlcpcb.com/capabilities/pcb-capabilities), [TI SNVA766](https://www.ti.com/lit/an/snva766/snva766.pdf), [TI BQ25616 package drawing](https://www.ti.com/lit/ds/symlink/bq25616.pdf). The repository's procurement/battery-path-primary-sources.json retains Molex and Littelfuse source provenance.
