# Glove v3 sensor laminate — 20 pressure + 20 PVDF locations

This is the mechanical starting assembly for the 20 locations in [`cells.json`](cells.json). Each location has its own two-electrode pressure element and two-face PVDF element; the cuff harness combines the pressure lower electrodes on the branch `VEXC2V5` return and the PVDF bottom faces on the branch `GND` return, as required by the v3 connector map. It is a cut-and-laminate prototype specification, not a released comfort or signal-isolation result.

## Material choice and evidence

The buyable PVDF starting material is **TE Connectivity / Measurement Specialties 1-1004347-0**, 28 µm PVDF with silver-ink electrodes, 8 × 5.5 in sheet. TE's metallized-film datasheet gives **40 µm total finished sheet thickness**, not 28 µm: 28 µm film plus the silver-ink electrodes. The datasheet also identifies silver ink as the compliant electrode suited to mechanical stress and easy lead attachment. Use the 8 × 11 in **1-1004346-0** only if the smaller sheet is unavailable; its finished thickness is 40 µm as well. See [`supplier-candidates.csv`](supplier-candidates.csv).

TE's polarity note defines the film's length/stretch axis as mechanical axis 1, width as axis 2, and thickness as axis 3. The cut template therefore marks the sheet's factory roll/stretch direction and places the 10 mm active dimension along that axis. The finished sheet has no guaranteed visible polarity mark in the distributor listing. During incoming inspection, mark the face/lead that produces positive voltage under the same compression test for every piece. Keep all pieces in the same orientation after marking; do not silently swap PVDF leads.

## One location, glove fabric to contact surface

1. Glove base: close-fitting fabric glove. Choose a smooth contact region on the palm-facing surface of each segment and keep the cell outside the flexion crease clearances recorded in `cells.json`.
2. Pressure lower electrode: 8 × 10 mm compliant conductive-fabric island, with a 2–3 mm tail extending toward the cuff. Bond it to the glove with a thin flexible textile adhesive around the perimeter only.
3. Pressure medium: one 8 × 10 mm Velostat/Linqstat island. The island must be cut separately so adjacent locations cannot share the resistive sheet.
4. Pressure upper electrode: a second 8 × 10 mm conductive-fabric island. Bring its lead along the side/back of the segment.
5. Electrical separator: 25–50 µm TPU film or polyester tape, larger than the pressure electrode, as a continuous insulating layer. Mechanical vibration transfers through the film; an electrical opening is not required. The separator must cover all pressure conductors before the PVDF element is placed.
6. PVDF element: cut a 10 × 14 mm rectangle from the pre-metallized sheet. The central 8 × 10 mm is the intended contact footprint. Because both electrodes cover the whole blank, the 10 × 14 mm blank remains electrically piezo-active, including its connection margin. Do not calculate its capacitance as an isolated 8 × 10 mm element. Stagger the two exposed electrode tabs on opposite ends so the top and bottom silver surfaces cannot short through the lead adhesive.
7. PVDF lead attachment: use **MG Chemicals 8331D-14G** silver conductive epoxy for the two 1.5 × 2.5 mm tab contacts. Apply one small controlled dot to the silver ink and overlap the stripped wire by 1.5 mm. Keep each dot on its own face and opposite end from the other face; leave the cut edge and a visible insulating gap between the two tab zones so epoxy cannot wick around the edge and short the faces. Cure on a flat jig at room temperature according to the manufacturer's datasheet; keep epoxy off the 8 × 10 mm active area.
8. PVDF cover: 25–50 µm TPU or polyester insulation over the full film and tab area, leaving the wire exit protected. Do not use the cover as a common electrode.
9. Strain relief: anchor each four-wire bundle to the glove 15–20 mm behind the cell with a 4 mm wide soft TPU/fabric bridge. Leave a 12–15 mm slack loop along the side/back of each finger. No lead, epoxy bead or connector may lie over a finger crease.

The finished local stack is therefore approximately: glove + pressure electrode + 0.2 mm Velostat + pressure electrode + separator + **40 µm TE sheet** + cover, plus adhesive and wire. The actual compressed thickness and feel are unknown until a coupon is measured; do not label the assembly “28 µm finished”.

## Lead and cuff termination

Use **Alpha Wire 5851** (30 AWG, 7/38 stranded silver-plated copper, PTFE, nominal 0.81 mm insulated diameter) for both pressure and PVDF pigtails. Strip only at the cell tab and cuff end. Keep pressure and PVDF leads as a labelled four-wire group only after they leave the active cell; at the branch breakout, join only the pressure lower leads to `VEXC2V5` and only the PVDF bottom leads to `GND`. Never join a pressure lead to the PVDF return. Do not twist the two PVDF wires tightly around the active film.

Terminate each branch at the actual v3 connector named in `wiring.csv` (`J_THUMB`, one finger connector, or `J_PALM_HEEL`). The branch has one signal pin per pressure/PVDF element plus one shared `VEXC2V5` pressure return and one shared `GND` PVDF return. The earlier 40-position pressure/PVDF header idea is not the v3 electrical interface and must not be used for this harness. Mark pin 1, add a printed strain-relief label, and verify continuity and isolation before connecting the cuff.

## Mechanical sequence

1. Print `cut-template.svg` at 100% and cut one paper coupon for each region. Confirm the 8 × 10 mm active footprint clears the wearer's crease by the specified margin.
2. Cut and label 20 Velostat islands and 20 conductive-fabric electrode pairs. Record the actual material batch.
3. Cut PVDF blanks with a sharp rotary blade on a clean sacrificial sheet. Keep the factory stretch direction aligned with the template arrow. Do not crease the film or scrape the silver ink.
4. Mark each PVDF pair's polarity using a repeatable compression jig. Record the selected top face in the harness sheet; relative polarity calibration is accepted when the supplier's face marking is absent.
5. Build one palm coupon and one distal-finger coupon. Measure pressure isolation, PVDF open-circuit response, tab resistance and flexion noise before making the remaining 18 locations.
6. Bond the pressure stack, place the separator, attach the PVDF element, apply the two leads and cure the epoxy on a flat jig.
7. Add the cover and strain-relief bridge. Route the four leads toward the cuff with a side/back loop and keep all adhesive joints outside the bending zone.
8. Perform continuity and isolation tests with the cuff disconnected: each pressure signal must be continuous to its own upper electrode, with no direct metallic short to another signal (finite resistance through the shared excitation and Velostat is expected); all pressure lower electrodes must be continuous to `VEXC2V5`; each PVDF signal face must be continuous to its own charge-amplifier input and isolated from every other signal; all PVDF return faces must be continuous to branch `GND`; the two PVDF faces at every location must remain isolated from one another.

## Validated versus unknown

**Validated by manufacturer documentation:** TE 1-1004347-0 is pre-metallized PVDF; nominal PVDF thickness is 28 µm; total sheet thickness is 40 µm for the silver-ink version; silver ink is intended for mechanically stressed film and lead attachment; the PVDF axis convention and polarity behavior are documented by TE's polarity application note; MG 8331D is a room-temperature-cure conductive epoxy product.

**Unknown until a physical coupon:** actual Sofia landed cost and delivery; distributor stock at order time; which PVDF face is positive on an unmarked sheet; tab adhesion after repeated flexion; pressure/PVDF mechanical cross-talk; long-term comfort; finished local thickness after adhesive and cover; wire fatigue at the finger-to-cuff transition; and whether the proposed 8 × 10 mm active footprint gives sufficient vibration signal.

This directory deliberately does not claim that the 20-location glove has been built or that the laminate meets the $150 complete-cuff target.
