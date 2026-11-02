# V4 one-glove power and packaging value engineering

Checked 2026-10-23. Scope is a cost-reduction review for one complete right-hand glove/cuff with the existing V4 capability contract:

- six hours continuous colour near-finger camera capture;
- 20 PVDF channels at 4 kHz per channel, 20 pressure channels, two `ISM330DHCXTR` IMUs;
- SD recording, BLE setup/status/preview, Wi-Fi video/full data, USB-C data and charging;
- one-button control, diffused RGB state indicator, protected single lithium cell and temperature-qualified charge path;
- soft glove/sensing stack and keyed plug-in harnesses.

No order, supplier contact, checkout, external upload or site submission was made. Prices and stock below are public snapshots. Bulgaria delivery is called out separately wherever it is not confirmed.

## What can be established today

There is no complete landed V4 one-glove cost in the current records. The priced baseline is incomplete: the retained catalog snapshot gives **US$54.61** for priced board components only; it excludes PCB fabrication, assembly, programming, test, shipping, VAT and several exact parts. The external kit adds the current Jauch battery at **€46.94 ex VAT** on the Farnell Bulgaria category row, the exact CamThink camera at **US$15** plus a Sofia cart shipping estimate of **US$25.50**, and the PVDF source sheet at **€184.19 per sheet**. Enclosure, tactile materials, harness preparation and final assembly remain quote items. A three-times reduction therefore cannot be claimed as a completed cost result yet.

The one-unit metric is cash required to build one glove. Shared purchasing can lower a future volume unit cost, but it does not reduce the one-unit outlay and is kept separate below.

| Area | Current retained evidence | Best sourced reduction candidate | Reduction that is actually supported |
|---|---|---|---|
| Battery | Jauch `250480`, 6,500 mAh minimum / 6,700 mAh typical, protected 1S2P, 69 × 38 × 20 mm, Farnell BG €46.94 ex VAT; Bulgaria stock/delivery open | Fullwat `LP906090-CI`, advertised 6,000 mAh, PCM, 90 × 60 × 9 mm, **€30.50 incl. Spanish VAT**, page says available; Conectrol SKU `LP906090-CI` | Rejected for the unchanged conservative six-hour requirement: 5.710591 h at the same 3.110011 W battery-input load. The public prices use different VAT bases and freight is open, so no battery saving is claimed. |
| Camera | CamThink `73.002.000035`, OV5640, 120° / 8 cm, US$15, MOQ 1, in stock; Sofia direct cart total US$40.50, 8–15 days | Keep this exact camera for one glove. A future five-unit arithmetic example is $15 + $25.50/5 = **$20.10 per camera**, if the cart keeps the same shipping rate. | One-unit cash remains US$40.50 before the unresolved tax discrepancy. Multi-unit freight is optional volume evidence and does not reduce one-unit outlay. |
| Rigid enclosure | Current audited enclosure allowance **74.18 g**; current CAD 112 × 104 × 45.5 mm, 47.1 mm with carrier | Sofia BG 3D Print public SLS PA12 rate **€0.625/g** gives a material-only reference of **€46.36** for 74.18 g. JLC3DP accepts MJF PA12 files and publishes process limits, but the V4 model quote was not obtained. | The €46.36 number is a material-rate reference, not a finished quote. Finishing, packing, shipping and the TPU/cut/optical parts remain. |
| PCBA assembly | No V4 assembly quote | AssemTec Europe publishes line setup ≥$34, stencil $27–68, SMT line start ≥$41, THT line start ≥$14, SMT solder point ≥$0.004 and THT point ≥$0.010. | A one-board floor before components and PCB is at least $102–143 for SMT setup, plus any THT setup and per-point costs. This is a cost floor, not a quote. |

For one glove, the current public evidence requires the cash outlay for the **€184.19 PVDF sheet**; its actual usable yield is unknown. A future batch can measure yield and allocate material per glove, but that optional volume model cannot be used as a one-unit three-times result. Record sheet yield, rejects and completed sensing stacks before making a volume claim.

## Ranked battery options

### Rejected: Fullwat `LP906090-CI` / 906090 pouch — fails the unchanged conservative six-hour case

Conectrol publishes **€30.50 incl. VAT**, “available”, for a Fullwat 3.7 V 6,000 mAh 906090 pack with PCM, 90 × 60 × 9 mm dimensions and a three-wire VHR-3N termination. The page states 0–45 °C charge, 6 A maximum charge and 12 A continuous discharge. Product page: <https://conectrol.com/producto/bateria-li-po-3-7v-6000mah-906090-con-pcm/>.

The existing conservative case is already evaluated at **3.110011 W at the battery input**, including converter loss and the allocated 190 mΩ path. Do not apply another converter/path factor. For the advertised nominal 6,000 mAh at 3.7 V:

`6.0 Ah × 3.7 V × 0.8 ÷ 3.110011 W = 5.710591 h`

This is **0.289409 h short** of six hours before any unproven capacity derating; 6,000 mAh is advertised nominal capacity, not a retained minimum. The pack is 22 mm wider (60 mm versus 38 mm) and at least 10.3 mm thinner than the selected Jauch 250480 after-cycling envelope. It cannot fit the current 69 × 38 × 20 mm battery pocket without a mechanical redesign; it also conflicts with the preferred 50.8 × 38.1 mm top footprint. The three-wire VHR-3N pinout, protection thresholds, UN38.3/MSDS, cell temperature sensor access and wire reach require verification. This candidate is recorded for traceability and is **not recommended for quote** under the unchanged contract. Bulgaria delivery and freight are not published on the product page.

### Rejected: Jauch `LP906090JH` / part `246525` — exact manufacturer-supported flat option, but fails the unchanged conservative six-hour case

Jauch’s own catalogue lists 6,000 mAh, 3.7 V and 93.5 × 60.5 × 9.0 mm. The repository’s distributor evidence records 9.7 mm after cycling. EVS Supply lists the exact Jauch pack with PCM and 70 mm wires at **US$40.10**, with an add-to-cart page and request-quote route: <https://www.evssupply.com/product/jauch-3-7v-6000mah-lithium-polymer-rechargeable-battery/>. The page does not expose stock quantity or Bulgaria shipping. Jauch’s catalogue: <https://www.jauch.com/en-INT/products/battery_technology/getPrm/batteries/Lithium%20Polymer%20Batteries/>.

At the advertised nominal 6,000 mAh, the corrected runtime is **5.710591 h** at 3.110011 W. The flat geometry has the same conservative-case failure and the same thermal, NTC, connector and first-article requirements. The public price is not comparable to the current Jauch price until VAT and delivered Bulgaria freight share a basis. This candidate is recorded for traceability and is **not recommended for quote** under the unchanged contract. The earlier Farnell BG listing for this part is marked no longer stocked at €70.74 ex VAT, so it is not an immediate Bulgaria route.

### Rejected: KBT `KBT-906090PL` — low-price, currently unavailable and fails the same conservative calculation

KBT publishes a 3.7 V, 6,000 mAh, 90 × 60 × 9 mm protected pack with 2C maximum continuous discharge at **US$9.59**; the page is marked **sold out** and says shipping is calculated at checkout: <https://www.kbt18650battery.com/products/kbt-906090pl-3-7v-6000mah-li-polymer-rechargeable-battery-with-2pin-2-54-jst-connector>.

Its advertised nominal 6,000 mAh also calculates to **5.710591 h** at 3.110011 W, and the page is marked sold out. It is a benchmark only, not a purchasable V4 source. The page does not establish an external NTC, exact protection thresholds, UN38.3/MSDS route or Bulgaria delivery. Do not include its price in a production cost claim or recommend it for quote.

### Battery options that fail the unchanged six-hour contract

Jauch `LP735977JH` / `246524` is publicly listed by DigiKey Marketplace at €31.48 with 100 reported in stock, but its 4,800 mAh minimum at 3.7 V gives only **4.568473 h** at 3.110011 W. It is rejected for the unchanged contract. The existing energy-budget and thermal protections must remain the authority; nominal mAh alone is not a substitute for measured usable energy. The selected Jauch 250480 remains the only listed battery with a conservative minimum-capacity result above six hours: `6.5 Ah × 3.6 V × 0.8 ÷ 3.110011 W = 6.019271 h`.

## Ranked camera options

### 1. CamThink `73.002.000035` — only currently supported exact match

The manufacturer shop maps variation 506 to **OV5640, 120° field of view, 8 cm fixed focus**, in stock, purchasable and MOQ 1 at US$15. The retained one-item Sofia cart returned US$25.50 Direct Delivery (US$40.50 product plus shipping, advertised 8–15 days) or DHL US$56.50 (US$71.50 product plus shipping, advertised 3–7 business days after dispatch). The direct rate says taxes/duties included while the general policy says DAP, so the US$40.50 total is not a verified all-in landed price. Processing is separately listed as 3–5 business days. Sources: <https://www.camthink.ai/store/ov5640/?attribute_pa_lens=120-8cm>, <https://www.camthink.ai/shipping-policy/>.

For one glove, retain the US$40.50 Sofia cart estimate as the cash outlay before its tax terms are resolved. A future five-module arithmetic example is US$20.10 per module if the one-module shipping rate remains unchanged; this is optional volume evidence, does not lower one-unit cash needed, and requires a real multi-quantity cart. Inspect the supplied flex tail, contact side and pin 1 against `FH12-24S-0.5SH(55)` before release.

### 2. Generic OV5640 120–130° DVP module — sample-only conditional

Alibaba’s public listing for Shenzhen Lonten shows **US$7.78–8.78, MOQ 1**, an OV5640 24-pin DVP camera described as 120–130°: <https://www.alibaba.com/search/page?SearchScene=imageTextSearch&productId=62212814481>. The public listing does not prove the V4 8 cm fixed-focus preset, near-finger image quality, FPC contact orientation, supplied tail length or Bulgaria shipping. It may reduce the module line price, but it cannot be counted until a sample passes the existing camera interface, focus, continuous JPEG, thermal and mechanical acceptance tests.

### 3. Generic fixed-focus OV5640 supplier module — batch-only conditional

Yingdeshun lists an OV5640 fixed-focus module at **US$18, MOQ 100**: <https://ydscam.en.made-in-china.com/product/GEOrlDcugbWH/China-Yds-Kr8-Ov5640-V2-2-Nir-5MP-Dvp-Parallel-Interface-No-IR-Filter-Fixed-Focus-Camera-Module.html>. The listing does not establish 120°/8 cm optics or the V4 tail. Its MOQ and absent Sofia freight make it irrelevant for a single glove and a weak route for a small batch.

No generic camera price should be substituted into the cost model until the exact optics and interface are demonstrated. The camera is a capability-critical part; a lower OV5640 sticker price alone does not preserve the contract.

## Ranked packaging and assembly routes

### 1. Sofia BG 3D Print: local PA12 SLS plus local soft parts

BG 3D Print publishes **€625/kg for PA12 SLS**, an instant quote, 2–5 working day standard production and one-day Bulgaria courier delivery; it advertises prototypes and series production from Sofia: <https://bg3dprint.com/en>, <https://bg3dprint.com/en/pricing>.

At the audited 74.18 g enclosure-material allowance, the public material-rate reference is €46.36. The actual quote must include powder/build minimums, finishing, the rigid base/lid/camera retainer, TPU carrier, grommets, gasket, optical PC window, button diaphragm and shipping separately. This route is attractive for one glove because it avoids international enclosure freight and gives a local fit-rework loop. Preserve the existing 112 × 104 × 45.5 mm shell interfaces, keyed cable glands and soft carrier unless a new mechanical release is made.

### 2. JLC3DP: quote the three rigid PA12 parts together

The existing quote-pack record identifies `rigid-base.stl`, `rigid-lid.stl` and `camera-rear-retainer.stl` as a suitable PA12-HP MJF group. JLC3DP publishes PA12 MJF process limits, a 72-hour build time and model-dependent instant quoting: <https://jlc3dp.com/help/article/pa12-hp-nylon>, <https://jlc3dp.com/3d-printing-quote>.

This may be cheaper at production volume, but the repository has no V4 price or Sofia shipping result and no one-unit saving is established. The current design still needs separately sourced TPU, silicone/foam, optical polycarbonate and fasteners. Keep those parts in a supplier quote line rather than assuming MJF can print the thin elastomers.

### 3. PCBWay: volume route only

PCBWay states assembly minimums as low as five pieces and accepts sourced or customer-supplied components: <https://m.pcbway.com/assembly-capabilities.html>. The official page gives no V4 quote, board price, programming/test price or Bulgaria shipping. It is a future volume route and does not establish a one-glove outlay.

### 4. AssemTec Europe: transparent setup floor for a single routed board

AssemTec publishes a calculator and guide prices: SMT line programming ≥US$34, stencil US$27–68, SMT line start ≥US$41, THT line start ≥US$14, SMT solder point ≥US$0.004 and THT solder point ≥US$0.010. Source: <https://assemteceurope.com/en/orders/pricing>.

For one V4 board, this is at least US$102–143 of SMT setup before the PCB, components, per-point charges, programming, test, freight and VAT; add the THT setup if used. It is useful for an apples-to-apples quote request and prevents a fictitious “cheap PCBA” allowance. MOQ is not stated publicly.

### 5. Local Sofia assemblers: delivery advantage, price still quote-only

The urgent procurement record identifies Micron-20 (assembly calculator; homepage advertises 24 h minimum and 1–3 day express), Comet (prototype SMT/THT, cable harnesses and layout), Zekeng (PCB assembly, firmware and 3D enclosure) and Bonev Electronics (prototype production and inspection). These are reasonable integration routes for a keyed soft-glove harness, but none has a public complete-cuff price. PRIMA-TECH-PRO publishes 10–12 working days after a complete free-issue kit and therefore needs an explicit expedite to fit a short prototype schedule. Source: `hardware/urgent-procurement-2026-10-22.md`.

The quote request should split: routed PCB fabrication; exact MPN placement; programming; camera and SD receiving; two IMU tile assembly; six keyed GH harnesses and one SH cable; PVDF/pressure laminate preparation; enclosure assembly; and recorded functional/thermal test. A supplier may consolidate these operations, but each price and acceptance obligation must remain visible.

## Thermal, electrical and mechanical gates for any cost option

The power budget is already at the boundary under its conservative case: **3.110011 W at the battery input, including converter loss and the allocated 190 mΩ path**, and 6.019271 h after the 20% reserve allocation for the selected Jauch 250480 minimum capacity. The six-hour result is a calculation, not a discharge proof. Every six-hour alternative must use the same battery-input formula and pass these gates:

1. retain the protected-cell charge path, BQ25616, USB-C limits, positive-entry `045102.5MRL` fuse, current/voltage trace capture and the documented ≤190 mΩ external path allocation;
2. verify the pack’s charge temperature range, maximum charge current, over-charge/over-discharge/over-current thresholds, UN38.3 and MSDS before release;
3. preserve the external Semitec 103AT-2 temperature measurement or document a tested equivalent sensor connection; a two-wire pack does not prove external NTC access;
4. run at least 30 minutes at thermal steady state with continuous camera, SD writes, Wi-Fi traffic, 20 × 4 kHz PVDF capture, pressure capture and both IMUs, recording battery current, all rails, frame timestamps, converter efficiency and pack/cell temperatures;
5. re-run the enclosure clearance and strain-relief checks for a 90 × 60 × 9–9.7 mm pouch. The flat pouch changes the battery footprint and heat-spreading surface, and its advertised nominal energy is below the selected pack's retained minimum energy;
6. preserve keyed GH housings/contacts, the SH IMU cable, soft textile carrier, finger glands, one-button mechanism and RGB light pipe. Removing keyed connections or moving the sensing stack to loose unkeyed wires is not a cost-equivalent glove.

## Can an integrated module cut cost without losing capability?

An off-the-shelf “ESP32 camera” module cannot be counted as an equivalent replacement. Typical modules change the camera bus or lens/focus, omit the V4 protected charger/current path, have no dual `ISM330DHCXTR` acquisition, and do not provide the 20-channel PVDF and 20-channel pressure front end. Even when a module includes ESP32, camera and microSD, the remaining board still needs the battery charger, rails, USB-C, protection, tactile ADC/multiplexers, two IMUs and keyed harness connectors.

A custom integrated carrier could remove the separate FH12 camera connector, some camera rail/level-shifter placements and one assembly interface. That is a new routed PCBA and a new camera/mechanical/thermal qualification item; its price must come from an actual turnkey quote using the V4 exact MPN BOM. There is no public price evidence here for a complete integrated module, so it is not part of the three-times cost case.

## Recommended sourcing sequence

1. Keep Jauch 250480 as the baseline. Record Fullwat `LP906090-CI` and Jauch `LP906090JH` as rejected under the unchanged conservative six-hour case; do not recommend either for quote unless the power requirement or measured operating case is deliberately revised. Any future battery review must include UN38.3/MSDS, cell protection thresholds, NTC pinout and wire drawing.
2. Use the exact CamThink 120°/8 cm camera for the first article. Run a multi-quantity cart only to measure the real shipping curve; treat generic OV5640 modules as samples until focus and FPC compatibility pass.
3. Ask BG 3D Print for a PA12 SLS quote using the 74.18 g allowance and the current rigid STL group, with finishing and local delivery itemised. In parallel, obtain one JLC3DP three-part PA12 quote when the external upload is explicitly authorized.
4. Send the routed V4 board plus exact BOM to AssemTec and one Sofia assembler for separate NRE, placement, programming, test, harness, textile, enclosure and shipping lines. Ask for quantity 1 and quantity 5 so setup amortisation is visible.
5. For one glove, retain the full PVDF sheet cash outlay in the cost model. A measured-yield batch model may be added separately for volume planning; it cannot be presented as a one-unit three-times reduction until the full PCBA quote, enclosure finish, harness labour, battery freight and Bulgaria VAT are known.

## Adversarial number audit

- **Battery power boundary:** `3.110011 W` is already the battery-input result from the conservative budget. It includes converter loss and the 190 mΩ path allocation. Applying a second 0.8 factor or returning to the 2.344438 W system-side figure double counts losses.
- **Selected battery:** `6.5 Ah × 3.6 V × 0.8 ÷ 3.110011 W = 6.019271 h`; this is the retained minimum-capacity arithmetic result. The 6.7 Ah typical result is 6.204480 h and is not the acceptance basis.
- **Every advertised 6 Ah flat option:** `6.0 Ah × 3.7 V × 0.8 ÷ 3.110011 W = 5.710591 h`; the 0.289409 h shortfall means both Fullwat and Jauch LP906090JH fail the unchanged conservative six-hour case before any capacity derating. Their 6,000 mAh values are advertised nominal values; a minimum capacity was not retained.
- **4.8 Ah flat option:** `4.8 Ah × 3.7 V × 0.8 ÷ 3.110011 W = 4.568473 h`; it is rejected.
- **Battery price comparison:** the earlier mixed-basis battery difference compared €30.50 incl. Spanish VAT with €46.94 ex VAT in Bulgaria and omitted delivered freight. It is removed as a saving claim.
- **Battery geometry:** 60 mm versus 38 mm is **22 mm wider**, not 30 mm wider. Length also grows from 69 mm to 90 mm; thickness falls from 20 mm to 9–9.7 mm.
- **Camera shipping:** US$40.50 is a one-module Sofia cart estimate. The US$20.10 five-unit arithmetic is optional volume sensitivity only and does not lower one-unit cash required.
- **PVDF:** €184.19 is the observed cash price for one sheet. Per-glove allocation needs measured yield and is a separate volume model.
- **Enclosure:** €46.36 is 74.18 g × €0.625/g material-rate arithmetic, not a finished SLS quote. It excludes build minimums, finishing, flexible parts, optical parts, fasteners and delivery.
- **Assembly:** the AssemTec US$102–143 figure is the published SMT setup floor (`34 + 27–68 + 41`), before PCB, components, per-point charges, programming, test, VAT and delivery. It is not an assumed complete PCBA price.
- **Three-times result:** no complete one-unit landed baseline exists, and the corrected six-hour battery candidates fail. A three-times one-glove reduction is therefore unproven.

## Evidence links

- System contract: `hardware/glove-v4/system-contract.json`
- Energy budget and six-hour calculation: `hardware/glove-v4/verification/energy-budget.json`
- Current BOM and exact critical-part evidence: `hardware/glove-v4/procurement/cost-status.md`, `hardware/glove-v4/procurement/bom-source-plan.csv`
- Exact Jauch 250480 evidence: `hardware/glove-v4/procurement/battery-candidate-jauch250480.md`
- Exact camera evidence and Sofia cart: `hardware/glove-v4/procurement/camera-sourcing.md`, `hardware/glove-v4/procurement/camera-sourcing.json`
- Enclosure mass and geometry: `hardware/glove-v4/enclosure/README.md`
- JLC3DP process review: `hardware/glove-v4/procurement/jlc3dp-enclosure.md`
- Corrected battery arithmetic: `hardware/glove-v4/value-engineering/power-packaging/battery-runtime-calculation.json`
