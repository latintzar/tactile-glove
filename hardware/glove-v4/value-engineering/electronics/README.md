# V4 electronics value engineering

**Review date:** 2026-10-23
**Scope:** read-only review of the canonical V4 cuff electronics; the report, native alternative-model runner and retained compressed traces are written in this pass.
**Decision boundary:** preserve 20 independent PVDF channels at 4 kHz/channel, 20 independent pressure channels at 50 Hz/channel, two `ISM330DHCXTR` devices at 833 Hz, continuous camera capture for six hours, and the existing BLE, Wi-Fi, microSD, USB-C, button, indicator, battery and protection functions.

## Finding

The retained evidence supports two actionable cost-reduction tracks; the shared-COM analog-topology candidate was evaluated and rejected:

1. RFQ cheaper same-spec 12 nF and 15 nF filter capacitors, then standardize the four repeated filter capacitor families around qualified MPNs.
2. First price the same-speed MCP33131D-10-E/MS (16-bit, 1 MSPS) against the current industrial-temperature part. Retain MCP33131D-05-I/MS (16-bit, 500 kSPS) as a secondary timing-change candidate only. The production schedule requires 81,000 conversions/s in aggregate, so the 500 kSPS part has 6.17x arithmetic throughput headroom before timing qualification.
3. The tested shared-COM alternative would replace U10/U26 with one-hot SN74HC139 arbitration, but the native OPA320 deck fails the 6 us/2 kohm dynamic case and both 24 us/10 kohm pressure cases. It has $0 booked savings and is retained below as a rejected candidate.

The first two tracks are quote and qualification work; neither has booked savings.

The older source prose recorded $54.61; the regenerated current historical JLC subset is **$54.5377 for 35 priced MPN rows**, as recorded in [the cost review](../cost-review.json); the complete landed glove is still open. The battery alone has a retained **£40.81 ex-VAT** observation and the camera has a retained **$15 module** observation, before board assembly, enclosure, sensor materials, tax and shipping. A 3× whole-glove reduction cannot be claimed from this evidence.

## Artifact basis

The review used these canonical artifacts:

- [`hardware/glove-v4/system-contract.json`](../../system-contract.json): channel counts, rates, camera, dual IMU, recording and physical interfaces.
- [`hardware/glove-v4/electrical/components.json`](../../electrical/components.json): 561 fitted placements, 107 unique MPNs, and the source topology. Subsystem counts are tactile 343, power 161, camera 37, IMU 5 and SD 15.
- [`hardware/glove-v4/procurement/cost-status.md`](../README.md) and [`bom-source-plan.csv`](../../procurement/bom-source-plan.csv): the retained point-in-time component price evidence and its exclusions.
- [`hardware/glove-v4/firmware/tactile_v4/main/core.hpp`](../../../../firmware/tactile_v4/main/core.hpp) and [`main/hardware.hpp`](../../../../firmware/tactile_v4/main/hardware.hpp): the actual 250 µs scan, bank/slot mapping and 6/24 µs waits.
- [`verification/differential-adc/README.md`](../../verification/differential-adc/README.md) and [`results.json`](../../verification/differential-adc/results.json): five completed modeled settling cases with 6 µs dynamic and 24 µs pressure waits.
- [`verification/analog-coverage-2026-10-23.md`](../../verification/analog-coverage-2026-10-23.md): inherited V3 signal-chain scope and V4 coverage gaps.
- [`verification/coupled-analog/README.md`](../../verification/coupled-analog/README.md) and [`results.json`](../../verification/coupled-analog/results.json): 289 canonical components stamped, seven bounded attempts, zero completed coupled cases.
- [`electrical/glove-v4-routing-candidate.kicad_pcb`](../../electrical/glove-v4-routing-candidate.kicad_pcb): eight copper layers (`F.Cu`, six internal copper layers and `B.Cu`).

## Current cost drivers

These are retained snapshot observations, not a fresh quote. Values below are the row prices in `bom-source-plan.csv`, multiplied by fitted quantity where applicable. Currency is kept as captured.

| Current row | Fitted | Snapshot extension | Why it matters |
|---|---:|---:|---|
| `MCP33131D-10-I/MS` | 1 | $12.2511 | Single 16-bit SAR ADC; largest board IC row. |
| `MCP6004T-I/ST` | 15 | $8.3895 | 20 charge amplifiers plus 40 active anti-alias filter channels. |
| `C0603C123J3GACAUTO` (12 nF) | 20 | $6.7280 | Filter stage capacitor family. |
| `C0603C153J3GACAUTO` (15 nF) | 20 | $6.9380 | Filter stage capacitor family. |
| `CD74HC4067M` | 4 | $4.8008 | Two dynamic banks and two pressure banks. |
| `ESP32-S3-WROOM-1-N8R8` | 1 | $4.30213 | BLE, Wi-Fi, USB and controller functions; retain. |
| `OPA320AIDBVR` | 2 | $2.7340 | Positive and negative SAR input drivers; retain unless a replacement passes the same settling case. |
| `OPA4323IPWR` | 1 | $1.7627 | Four bank followers; candidate for the shared-COM topology below. |
| `REF3330AIDBZR` | 1 | $1.6384 | ADC reference; retain the reference function and local reservoir. |

The ADC, 15 quad op-amps, the two 20-piece capacitor families and four 4067s account for about **$39.11** in retained row extensions, roughly **72% of the stated $54.61 priced-board subtotal**. The percentage is a prioritization aid: the source rows are point-in-time snapshots and the complete board subtotal excludes assembly, PCB, external kit and landed logistics.

The 20 `BAV199` clamps, 20 100 kΩ PVDF input limiters, per-channel 22 MΩ/470 pF charge feedback, VEXC/VMID network, ADC charge buckets, reference reservoir and 1.8 V ADC LDO are functional signal, protection or bias elements. They are not counted as disposable cost.

## Opportunity 1 — same-spec filter capacitor sourcing

**Current topology:** each of 20 PVDF channels has two active Sallen-Key sections ahead of the dynamic mux. The repeated values are 14.7 kΩ/14.7 kΩ with 12 nF/10 nF and 27.4 kΩ/27.4 kΩ with 15 nF/2.2 nF. This is 40 op-amp filter channels and 80 filter capacitors. The retained 12 nF and 15 nF rows alone are $13.666 in the captured snapshot.

**Exact preserve-function action:** keep the values, voltage rating, temperature coefficient, tolerance and package required by the filter calculation; RFQ alternate MPNs at the same values. A second step can qualify a common 0603 X7R family only after the pole, Q, dielectric-bias and temperature spread are included in the filter and alias-error budget. Keep the 10 nF and 2.2 nF values until that review closes.

**Proven calculation:** for equal-R Sallen-Key stages, `fc = 1/(2πR√(Cfb·Cg))` and `Q = 0.5√(Cfb/Cg)`. The current nominal pairs give approximately 989 Hz/Q 0.548 and 1,011 Hz/Q 1.306, matching the inherited design intent. This is why a cheaper capacitor must be same-spec or requalified as a pair; deleting or casually substituting the filter changes alias rejection and waveform gain.

**Savings status:** the $13.666 is real captured spend in the component snapshot. An alternative unit price and an assembly quote are absent, so no dollar saving is booked. A useful RFQ acceptance target is a materially lower price for 40 pieces while retaining the above electrical limits; the actual saving is `40 × (current unit price − accepted unit price)` and must be filled from a supplier quote.

## Opportunity 2 — 500 kSPS member of the same ADC family

**Candidate:** `MCP33131D-05-I/MS`, the same family and 16-bit differential architecture at 500 kSPS. The official Microchip data sheet identifies the `-10` as 1 MSPS/16-bit and the `-05` as 500 kSPS/16-bit. The current row is `$12.2511`. Exact market observations now recorded for the same family are Newark `MCP33131D-05-E/MS` at `$4.29`, 1,769 reported in stock ([Newark listing](https://www.newark.com/microchip/mcp33131d-05-e-ms/adc-16bit-500ksps-differential/dp/94AC7653)) and Mouser Canada `MCP33131D-10-E-MS` at `CAD 7.23` ([Mouser listing](https://www.mouser.ca/ProductDetail/Microchip-Technology/MCP33131D-10-E-MS?qs=byeeYqUIh0NhU4NZQbhNiA%3D%3D)). These are sourcing observations, not booked savings; `-E` versus `-I` temperature/qualification grade and the exact MS package must be reconciled against the official data sheet. Do not select the 500 kSPS part when the broader-temperature 1 MSPS `-10-E/MS` is cheaper and qualified.

**Throughput calculation:** the firmware reads all 20 dynamic channels every 250 µs (`20 × 4,000 = 80,000 conversions/s`) and advances one pressure channel every fourth frame (`20 × 50 = 1,000 conversions/s`). Total demand is **81,000 conversions/s**. The 1 MSPS part has 12.35× arithmetic headroom; the 500 kSPS member has **6.17×**. The modeled scan budget already allocates 144 µs to dynamic/pressure settling plus 21 µs conversion and 21 µs serial clocks, leaving 64 µs in the 250 µs frame. The 500 kSPS device's 2 µs conversion period adds at most roughly 1 µs per dynamic conversion relative to the current 1 µs period, or about 20 µs/frame under the present schedule; this leaves roughly 44 µs before other overhead.

**Qualification gates:** run the native ADC campaign with the `-05` model, preserve 16-bit output and the existing 6/24 µs waits, then scope CNV, SCK, SDO and the real mux transition under camera/Wi-Fi/BLE/SD load. The 500 kSPS arithmetic supports a candidate; it does not prove timing, reference kickback or thermal equivalence.

**Savings status:** price and availability are open. This is a strong RFQ candidate because the replacement remains 16-bit and the current schedule is far below 500 kSPS, but no savings should be entered until an exact MPN quote and native timing result exist.

## Rejected candidate — one-hot shared-COM mux bus

The native direct-bus deck in [shared-com-spice.md](shared-com-spice.md) rejects this candidate for the current signal contract. Its raw U10 plus U26 row extension is $2.0919 before the decoder and layout delta, so booked savings are **$0** and this topology is not a ranked V4 action. The topology below is retained as an explicit record of the tested alternative.

### Proposed net topology

Retain the four `CD74HC4067M` devices and their 16 sensor inputs each:

```text
             MUX_A[3:0] shared to U6..U9
MUX_BANK[1:0] -> SN74HC139 -> EN_U6..EN_U9 (one active-low enable)

U6 COM ─┐
U7 COM ─┼── MUX_COM_BUS ── U5 OPA320 ADC driver ── 22 Ω/1 nF bucket ── U4 MCP33131
U8 COM ─┤
U9 COM ─┘
```

The current firmware already emits `bank = 0..3` and `slot = 0..9`; the existing six-bit `SN74AHC595` has `MUX_BANK0/1` outputs. Use the `SN74HC139` first decoder half with those two bank bits, wire its four active-low outputs to the four 4067 EN pins, and tie the second decoder half disabled. Change each 4067's current grounded EN to its decoded enable. Leave all channel input wiring and slot values unchanged. The bank+slot pair remains the channel identity: banks 0/1 are pressure and banks 2/3 are PVDF.

Remove `U10 CD74HC4052M` and `U26 OPA4323IPWR`. Keep `U5 OPA320AIDBVR`, `U29 OPA320AIDBVR`, the ADC charge buckets, and the differential reference/bias path. Remove the four U26 local decoupling placements only after the power-integrity check; add the decoder's local 100 nF bypass. The expected placement delta is approximately **−2 analog ICs, −4 bank-buffer channels, +1 small decoder**, plus a few local capacitors. The placement and routing reduction was the reason to test this candidate, but the native pressure and worst-case dynamic settling failures prevent claiming assembly or BOM savings.

### Why the signal contract can remain intact

- Channel identity stays explicit in the firmware's bank+slot address; no matrix row/column inference is introduced.
- The 4067 data sheet specifies an enable that places all switches in the off state and break-before-make behavior. The 139 data sheet specifies one selected low output and all other outputs high; its typical propagation delay is 10 ns. Both are small relative to the existing 6 µs dynamic and 24 µs pressure waits.
- The existing ADC driver and 22 Ω/1 nF charge bucket remain in the signal path. The shared bus adds switch and disabled-COM parasitics, while removing one 4052 switch and four follower stages.
- Using the current modeled 1–2 kΩ mux resistance as a conservative upper bound, the direct-bus RC with the 1 nF bucket is approximately `(2,000 Ω + 22 Ω) × 1 nF = 2.022 µs`; 6 µs is 2.97 time constants and 24 µs is 11.87 time constants. The present differential campaign already treats 1–2 kΩ and doubled capacitance as explicit stress assumptions. This is a first-order check, not a pass: the OPA320 loop, four disabled COM capacitances, charge injection and off leakage need a real direct-bus deck.

### Required proof before adoption

Build a V4 deck with the exact one-hot decoder timing, one active 4067, three disabled 4067 COMs, the OPA320 positive and negative paths, the existing 22 Ω/1 nF buckets, REF3330 reservoir, VEXC/VMID load and one PVDF/pressure transition. Run all 20 dynamic slots and all 20 pressure slots, record selected-channel residual, adjacent-bank crosstalk and bus recovery, then bench-scope the same sequence with the camera and radios active. The existing coupled-analog campaign has zero completed full-network cases, so this topology must carry its own evidence.

## Candidates that look cheap but break the contract

The repeated filter op-amps, charge feedback, clamps, bias network and ADC buckets are required for the current signal contract. A shared post-mux filter, dropping the 20 PVDF clamps, replacing the differential ADC with the ESP32 internal ADC, or removing the pressure wait would make the BOM shorter while changing alias rejection, overload recovery, pressure settling, spatial identity or resolution. Those are false savings for this review.

Integrated multichannel ADCs were checked as alternatives. TI's `ADS7953` is 16-channel/1 MSPS but only 12-bit; it cannot claim the current 16-bit signal quality. Analog Devices' `AD7689` is 16-bit/8-channel/250 kSPS, but five devices are required for 40 channels and its listed 1k price starts at $9.20 each, before the required PVDF charge amplifiers and filters. TI's `ADS8588S` and ADI's `AD7606B` integrate useful front ends but require five 8-channel devices for 40 channels and add 5 V analog power, level/range changes and substantial package/assembly cost. They are architecture alternatives for a new product generation, not defensible V4 cost reductions.

## Ranked recommendation

| Rank | Action | Evidence level | Expected effect |
|---:|---|---|---|
| 1 | RFQ same-spec 12 nF/15 nF MPNs; qualify dielectric and tolerance in the existing filter model | Proven current cost driver; proposed alternate | Lowest electrical risk; direct component-price reduction if the quote confirms it. |
| 2 | Price and model `MCP33131D-05-I/MS` | Official 16-bit/500 kSPS specification; timing is calculated, not measured | Potentially large single-row reduction with unchanged nominal resolution; exact quote and timing proof required. |
| 3 | Reject the direct shared-COM bus for V4; retain the current bank followers | Native OPA320 deck: pressure and 2 kΩ dynamic cases fail half-LSB settling | **$0 booked savings**; revisit only as a new buffered topology with fresh evidence. |
| 4 | Preserve all 20 per-channel active filter paths and protection while the above evidence closes | Current topology and partial SPICE evidence | Prevents a false 3× claim based on removing signal-critical parts. |

## Source links

- [Microchip MCP33131D-10 product page](https://www.microchip.com/en-us/product/mcp33131d-10) and [MCP33131D data sheet](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP33131D-Data-Sheet-DS20005947B.pdf)
- [TI CD74HC4067/CD74HCT4067 data sheet](https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf)
- [TI SN74HC139 data sheet](https://www.ti.com/lit/ds/symlink/sn74hc139.pdf)
- [TI ADS7953 product page](https://www.ti.com/product/ADS7953)
- [Analog Devices AD7689 product page](https://www.analog.com/en/products/ad7689.html)
- [TI ADS8588S product page](https://www.ti.com/product/ADS8588S)
- [Analog Devices AD7606B product page](https://www.analog.com/en/products/ad7606b.html)

**Bottom line for procurement:** obtain exact quotes for qualified 12/15 nF capacitor alternates and the qualified 1 MSPS/500 kSPS ADC variants. The direct shared-COM candidate has $0 booked savings after native settling rejection; do not RFQ its PCB/assembly delta as a V4 action. Until those quotes and the direct-bus/native timing tests exist, report the opportunity set and the current $54.61 priced-board baseline; do not publish a 3× total-cost claim.
