# JLC3DP enclosure sourcing note

**Checked:** 2026-10-23
**Scope:** V4 cuff enclosure, rigid body 112 × 104 × 45.5 mm; window-inclusive footprint 112 × 105.6 mm; height with flat carrier 47.1 mm; future slim target approximately 51 × 38 mm. This is a read-only process review. No proprietary CAD was uploaded and no order was placed.

## Recommended process split

| Part group | Proposed process | Procurement status |
|---|---|---|
| `rigid-base.stl`, `rigid-lid.stl`, `camera-rear-retainer.stl` | JLC3DP PA12-HP Nylon MJF | Three-file shell quote candidate; critical finishing reviewed separately |
| Three button pieces | Precision PA12 print/sprue and finishing, or machined PA12 | Small-part process acceptance required |
| Flat strap carrier | TPU95A FDM quote candidate | Wall/load validation required |
| Cable grommets, blanking plugs, service caps, battery belt, hand-tile pocket/cover | Separately qualified cast/precision elastomer | Published JLC FDM minimum part size excludes small parts |
| `button-silicone-diaphragm.stl`, `lid-perimeter-gasket.stl`, foam pads and camera shims | Die-cut or molded silicone/foam supplied separately | Separate fabrication route |
| `camera-window-clear-pc.stl` | Ø22 mm disk cut from specified 1 mm RS PRO 7698720 clear PC sheet; 3M VHB LSE-060WF overlap bond | Flatness, bond preparation and optical inspection required |
| `rgb-lightpipe.stl` | Machined/optical polycarbonate | Separate fabrication route |
| `camera-module-envelope.stl`, `camera-flex-envelope.stl`, `battery-envelope.stl`, `battery-ntc-envelope.stl`, `pcb-envelope.stl`, `hand-tile-pcb-envelope.stl` | Inspection geometry only | Retain outside the production upload set |

PA12-HP is the strongest direct JLC3DP fit for the rigid shell. JLC lists MJF PA12 at 1 mm wall thickness, ±0.3 mm tolerance within 100 mm and ±0.4% above 100 mm, with a 370 × 276 × 360 mm build envelope. The current cuff fits that envelope. The PA12 material page lists 72 hours of build time; transit to Sofia and any finishing time are additional and require checkout confirmation. For long shell faces, retain the CAD's ribs and first-article dimensional coupon; JLC's enclosure guidance gives 1.5–2.5 mm as a practical typical wall range even though 1 mm is the listed process wall value.

JLC's MJF design guide lists 0.2–0.4 mm clearance for assembled parts, 0.6 mm for moving/connecting parts, 1.5 mm minimum holes, 2.5 mm escape holes, 2.0 mm columns and 0.6 mm thread pitch. The current M2 nut-and-screw strategy is preferable to relying on a printed M2 thread. JLC's general capabilities page mentions machined M6-and-larger threads and threaded inserts; M2 insert capability remains unlisted for this part.

The public JLC TPU material page describes **FDM TPU, 95A**, with 1.6 mm recommended wall, 1.2 mm minimum, ±0.3 mm within 100 mm, and a 250 mm cube maximum. The enclosure CAD calls for TPU90A precision SLS/cast and includes thin liners and grommets. Quote those parts as a separate supplier question or coupon; TPU90A process equivalence needs confirmation against JLC's published 95A FDM material. The revised flat carrier has1.6 mm load-bearing sections. JLC lists a30×30×15 mm minimum FDM part; small glands/caps/tile parts require another accepted process. The0.20 mm camera liner remains a formed-film part.

JLC3DP's own mold-making guidance describes silicone through a printed master and casting route. The specified 0.60 mm VMQ button diaphragm and perimeter silicone gasket therefore use die-cut/molded silicone supply. A JLC SLA or PA12 master is a possible tooling quote, subject to release of the measured button and gasket geometry.

For SLA, JLC's design guide lists ±0.2 mm within 100 mm, ±0.3% above 100 mm, and 0.8 mm recommended wall thickness. It is suitable for a mold/master or fit-check part. The clear camera window remains specified as optical polycarbonate rather than printed resin.

JLC lists natural gray PA12 and offers post-processing such as blasting, dyeing, painting and vapor smoothing through its 3D-printing capabilities. Request the finish on the quote and measure critical fits after finishing; keep screw seats, gasket seats, button bores and camera datums masked or dimensionally checked.

## Public quote workflow checked

The public [JLC3DP instant quote page](https://jlc3dp.com/3d-printing-quote) accepts STL, STP/STEP, OBJ and 3MF. Before a model is uploaded it displays the global geometry gates of wall thickness above 1.2 mm and thinnest part at least 0.8 mm; the price remains model-dependent until upload. The page exposes upload history after sign-in, a total-price panel, shipping/weight fields and `SAVE TO CART`/submit controls. Use the public capability/quotation flow to check your selected material groups.

The final enclosure quote should contain exactly these three current-hash files, each quantity one:

- `rigid-base.stl` — PA12-HP MJF, natural gray.
- `rigid-lid.stl` — PA12-HP MJF, natural gray.
- `camera-rear-retainer.stl` — PA12-HP MJF, natural gray.

The PA12-HP source page lists natural gray and a 72-hour build time. JLC's PA12S-HP page lists black and gray as a separate MJF material; black therefore requires a separate PA12S-HP price/material comparison rather than being assumed as a PA12-HP finish. The public MJF page says production can start from two days; Sofia delivery time and shipping cost appear only after the model quote and should be recorded separately from manufacturing lead time.

Existing local JLC helpers target the V3 PCB/PCBA cart and contain hard-coded V3 paths/URLs. A final V4 enclosure run needs a fresh 3D-quote script using the three final STL hashes and the opaque existing browser state, with inspection solids and all other enclosure geometries left out.

The [print manifest](../enclosure/print-manifest.json) identifies the material groups. Prepare your own quotation pack after reviewing the process and tolerance requirements; supplier acceptance and landed pricing remain physical-build steps.

## Current file readiness

The production STL set and material assignments are in `hardware/glove-v4/enclosure/print-manifest.json`. It lists 48 solids in total: 42 manufactured-part geometries and six inspection envelopes. The meshes independently reload as closed solids and the nominal collision audit is complete, but the manifest remains `manufacturing_released: false`.

The release gates recorded in `clearance-report.json` are:

1. Measure the selected SDP/SI S78CSYM030035008 catalog spring load/rate and fit the captured tip to the actual switch height.
2. Measure the supplied camera tail and lens datum before selecting carrier shims.
3. Verify fitted component and wire bundle dimensions against the sourced maximum-height envelopes.
4. Validate TPU gland compression, gasket compression, diaphragm/window bonding and dust/splash behavior.
5. Verify dimensional coupons, PCB clamp compression, strap retention, thermal behavior, battery assembly, finished mass and fit.

The current geometry can support a **non-binding process/material review** once the intended material groups are separated. The thin camera lugs and button ledges have been repaired, the moving diametral clearances increased to0.8 mm, and the curved mount replaced by a flat carrier. First-article fabrication still requires accepted processes or finishing for the critical fits, small elastomer pieces, optical parts and button, plus qualified wire bends and seal compression. Production qualification then adds the physical first-article checks above. A nominal collision pass alone is insufficient for either stage.

## Primary JLC sources

- [PA12-HP Nylon](https://jlc3dp.com/help/article/pa12-hp-nylon) — MJF, wall, tolerance, build envelope and material properties.
- [HP MJF design guidelines](https://jlc3dp.com/3d-printing/multi-jet-fusion?from=news) — clearances, holes, columns, escape holes and thread pitch.
- [3D printing design guideline](https://jlc3dp.com/help/article/3d-printing-design-guideline) — SLA/MJF/SLS tolerances and hole guidance.
- [TPU](https://jlc3dp.com/help/article/tpu) — public TPU process, hardness, wall and tolerance values.
- [MJF production parts](https://jlc3dp.com/blog/mjf-for-production-parts) — enclosure, snap-fit and finishing guidance.
- [3D-printed mold making](https://jlc3dp.com/blog/3d-printed-mold-making) — silicone casting and printed-master route.
- [JLC3DP capabilities](https://jlc3dp.com/capabilities/3d-printing-service) — finishing and insert-service overview.
