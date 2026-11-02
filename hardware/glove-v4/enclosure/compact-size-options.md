# Cuff size and fabrication audit

2026-10-23. Retain this electronics layout as the current proof unit and use its flat textile carrier. Approaching the requested50.8×38.1mm footprint requires a separately scoped electronics and battery arrangement. The present board and battery independently exceed that footprint; the six-hour continuous-camera requirement stays in the system contract.

The body is112×104×45.5mm. Including the overlap window and flat carrier, the CAD assembly is112×105.6×47.1mm before textile. Manufactured cuff parts total74.180g, a1.670g increase over the preceding72.510g checkpoint from the window/lid/connector-fit changes. Battery100g, main PCB24g and electronics/fastener allowance20–35g produce218.18–233.18g before external textile and harness. These are solid-volume material estimates, with exact per-part densities in clearance-report.json.

## Actual size limits

| Dimension | Geometry that establishes it |
|---|---|
| Width112mm, X−6…106 | PCB X0…100; side clamps, gland/service collars and screw columns occupy the6mm margins. The shell wall is1.3mm. A board-plus-two-walls lower bound of102.6mm omits those working interfaces. |
| Body length104mm, Y−12…92 | PCB Y0…80; MCU maximum reachesY86.1; SD reaches84.745. Camera lens isY−10.515 and front glands share the front wall. The rear contains service access and fasteners. |
| Assembled length105.6mm | Flat stock-PC window plus tape extends1.6mm in front of the body. Tolerance extremes allow2.09mm projection; this is recorded separately from nominal CAD size. |
| Body height45.5mm | Floor0…1.3; foam1.3…3; padded battery3…24; belt up to25; lowest underside package26.1; PCB29…30.6. Mated Micro-Fit conservative maximum reaches41.86. The NTC wire bend reaches43.65. Lid underside44.2; outer face45.5. |
| Button height constraint | Tip flange top38.7 +installed spring5.2 =cap underside43.9; cap1.0 reaches44.9; diaphragm0.6 reaches45.5. Changing only the NTC connector to right-angle saves no height. |
| Flat attachment | Carrier extends1.6mm below the case, replacing the previous8mm curved saddle. The resulting47.1mm assembly height saves6.4mm without moving electronics. |

All545 former generic package-height instances now use documented manufacturer maxima plus a separate0.20mm mounting allowance. The actual561 main-board and seven hand-tile component solids are exported in component-envelopes.json. Micro-Fit, fuse and wire service geometry use their specific drawing/assembly bounds. See height-evidence/README.md and vertical-packing-check.md.

The padded battery footprint72×39mm is2,808mm². The requested50.8×38.1mm outer footprint is1,935.48mm² with a63.5mm diagonal; its diagonal is shorter than the battery's72mm length. The existing PCB is8,000mm². The current561-part KiCad courtyard-polygon audit totals7,676.96mm² over both faces. Even excluding the full MCU courtyard and all connectors leaves4,963.82mm², exceeding the requested footprint's two faces3,870.96mm² before routing and walls. These values come from ../electrical/size-feasibility.json at board SHA4dffc8247005fc48f812adcb06ea96a801659cdc4e144911322e7c8df1c25b9d; they bound this BOM, not a redesigned product.

## Bounded size options

| Option | Finding |
|---|---|
| Current board/battery with flat mount | Implemented112×104×45.5mm body;112×105.6×47.1mm assembled before textile. |
| Narrower shell with this placement | Requires redesigning actual clamps, ports and bosses.102.6mm board-plus-wall width is only a lower bound, not a verified enclosure. |
| Lower PCB or lid | Current camera fold/tail plane and fitted button set-point move with the board. The belt-to-lowest-component gap is1.1mm. The button independently fixes45.5mm top height. No simple translation preserves the interfaces. |
| Flatter battery, same PCB | Jauch LP906090JH nominal9×60.5×93.5mm and minimum6000mAh is a separate option screen. Its larger footprint requires a different bay; swelling/fit and the updated full-path runtime budget must be proven before selection. No runtime claim or CAD substitution is made here. |
| Approximately51×38mm product | Requires different board/BOM packing and battery distribution. Splitting/stacking boards consumes area/height and requires a concrete routed implementation. |

The optional flat pack's [manufacturer drawing](https://www.jauch.com/downloadfile/5bf529a732a3120f6edf04743f55a5dcb/6000mah_-_lp906090jh_1s1p_2_wire_70mm.pdf) is a dimensional source for that separate option.

## Fabrication findings

JLC PA12-HP lists1mm minimum wall and±0.3mm tolerance below100mm, or±0.4% above100mm. The112/104mm spans therefore have±0.448/±0.416mm published tolerances. General quote preflight requests broad walls above1.2mm; the current broad shell faces use1.3mm. Their MJF guide recommends0.6mm moving clearance and2.5mm powder escape holes. Local fit specifications require supplier acceptance and finishing. [PA12 specification](https://jlc3dp.com/help/article/pa12-hp-nylon), [MJF design guide](https://jlc3dp.com/3d-printing/multi-jet-fusion?from=news).

| Feature | Current implementation and process requirement |
|---|---|
| Rigid features | Shell/floor/lid1.3mm; button retaining ledges≥1mm; stop/bridges1.5mm. Large-panel strength remains a physical acceptance test. |
| Button |0.8mm diametral moving clearances; guide pin finish≤2.05mm; factory gap0.15±0.10mm and stop0.80±0.05mm. Catalog spring SDP/SI S78CSYM030035008 replaces the custom coil; receiving force/rate checks and switch overload/cycle tests remain. |
| Camera fasteners |Ø7.6mm lugs,2.65mm nut-pocket radius and≥1.10mm local radial material;5.3mm slots pass the4.619mm nut corner width. Local wall acceptance is needed. |
| Assembly access | Independent nut insertion andØ3mm camera/lid screwdriver checks. Fit camera before PCB/battery. Hollow columns have2.8mm powder ports. |
| Battery connector/harness | Direct AWG22-compatible Micro-Fit replaces the PH power adapter. Two explicit assembly variants: original leads after measured reach acceptance, or35mm addedAWG22 per lead with5mm overlap. CompleteR4 fallback routes pass through staggeredØ4×16mm sleeves and retain3.576mm worst conservative reach margin. |
| Lid/seal | Rear screws at(24,86)/(36,86) clear Micro-Fit/SD/RF; polymer ribs stiffen the rear and left spans. The longest adjacent screw chord is113.2mm. Specify a measured0.60±0.05mm installed gap for0.8mm foam around the whole perimeter; supplier flatness/fixture/load-uniformity acceptance is essential. |
| Window |Ø22±0.2mm stock1mm PC overlap disk,3M VHB LSE-060WF ringOD22/ID17, flatØ24mm land. Land flatness≤0.2mm, registration≤0.3mm; depowder/dry/prepare nylon and apply Primer94/tape per window-fabrication.md. Full tolerance FoV audit passes. |
| Glands | Cast intact and knife-split without removing material. Cable diameter, compression, pull and seal acceptance remain. Each wired port replaces only its own plug in the audit. |
| PCB capture | Four ledges and measured compressible pads load actual board edges. Rear-left clamp moved to(18,80) for the new battery connector. |
| Carrier | Flat1.6mm rails and loops use textile as the skin-contact layer. |

JLC TPU is95A FDM with minimum build size30×30×15mm, minimum wall1.2mm and default15% infill. The small glands/caps/tile parts require a separately accepted cast/precision route; the flat carrier remains a quote candidate. Mass uses actual solid volume. [JLC TPU specification](https://jlc3dp.com/help/article/tpu).

The manifest separates42 manufactured solids and six inspection envelopes. It lists print/finish, small-elastomer, optical, foam and harness process acceptance separately from physical first-article tests. first_article_fabrication_ready remains false. Implemented and parked simplifications are recorded in dfm-simplifications.md.
