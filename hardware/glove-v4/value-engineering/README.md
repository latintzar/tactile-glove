# Same-capability glove cost reduction

**Target:** one-third of the complete delivered cost for one right-hand glove. Keep 20 independent local pressure and vibration locations, acquisition quality/rates, both ISM330DHCX sensors, continuous camera, six-hour operation, SD, Bluetooth/Wi-Fi/USB, charge protection, button, indicator, keyed assembly and glove feel. The [locked requirements](requirements-lock.json) preserve the full brief. The compact cuff and tracking/texture demonstration requirements remain open engineering work in the baseline.

**Current result:** the first cost screen and a native analog alternative simulation are complete. A cheaper complete design and a threefold saving are still unestablished. Both complete delivered totals remain unknown. The canonical hardware is unchanged; the selected-cost and manufacturing gates remain open.

## Decisions from this pass

| Change | Evidence | Decision |
|---|---|---|
| Replace a complete Alpha 5851 industrial wire spool with soft 30 AWG silicone wire | One Alpha 100 ft spool observed at $143.30; two Adafruit 3164 50 ft spools at $9.90 total. Adafruit lists 0.8 mm OD and 331 Ω/km; its nominal OD and gauge fit the published GH contact envelope. | Prioritize a factory harness qualification. $133.40 is a goods-price difference, not an approved or delivered saving. Preserve labels, lead mapping, actual cut lengths, crimp pull, strain relief, bundle fit, leakage/capacitance and movement-noise checks. |
| Reduce expensive one-off component loading | Actual PCB: 561 placements, 107 MPNs, 183 front/378 back; JLC's public Standard loading rate produces a $163.71 scenario for 107 distinct types before other charges. | Consolidate equivalent part types and compare complete factory quotes. The scenario is not a quote; exact billable groups may differ. |
| Change to Economic assembly | JLC requires single-sided placement, supported 2/4/6-layer stack and at least 0.5 mm BGA pitch. Current PCB is double-sided, eight-layer and includes a 0.4 mm BGA. | A layer-count change alone cannot deliver that saving. A smaller, less complex layout must also preserve all electrical and assembly checks. |
| Remove bank followers and final analog multiplexer | Four native full-step cases completed with original TI amplifier models. Three fail existing acquisition waits; worst pressure residual is 5.262 mV versus a 45.8 µV limit. | Reject this candidate. Book $0 savings. Keep the buffered topology. |
| Substitute a cheaper 6 Ah battery | Existing battery-input power includes converter and external path loss. The candidate's nominal energy yields 5.7106 h after the same reserve. | Reject at the unchanged load. Preserve six-hour capture. |
| Use pre-terminated TE LDT0-028K piezo strips | Commercial stock/price exists, but 13 × 25 mm backed film replaces 10 × 14 mm bare film and increases thickness. | Exclude from a same-construction saving until fit, feel and transfer response satisfy the existing requirements. |
| Re-source ADC and C0G filter capacitors | Exact 16-bit ADC variants and same-value dielectric requirements identified; 1 MSPS extended-temperature option should be checked before considering a slower member. | Continue exact sourcing; retain timing and signal performance. Candidate delivered prices and integration checks remain open. |

The wire sources are [Adafruit 3164](https://www.adafruit.com/product/3164) and [Mouser's matching part](https://www.mouser.com/en/ProductDetail/Adafruit/3164?qs=A50fv7uxK7U20Q2IpuyE0g%3D%3D). Assembly observations use the [JLC price schedule](https://jlcpcb.com/help/article/pcb-assembly-price) and [capability table](https://jlcpcb.com/capabilities/pcb-assembly-capabilities), checked 23 October 2026. Price, stock and delivery must be reconfirmed for the actual basket.

## Cost basis

The regenerated current CSV subset is **$54.5377 for 35 historical JLC-priced MPN rows / 414 placements**. This is narrower than the older $54.61 prose snapshot: it excludes unpriced components and separately captured Comet prices. [cost-review.json](cost-review.json) records the exact CSV hash and each included row. Neither subtotal is a complete cuff cost.

The primary metric is cash needed for **one usable glove**. A supplier's mandatory two-PCBA order, entire sheet/spool/syringe, shipping, tax, factory preparation, flashing and testing all count. Spare material has residual value, but allocating it to imaginary future gloves does not reduce today's payment. A factory can charge for consumed material from its own stock only when its actual quotation offers that service.

Keep currencies and VAT basis separate until a dated conversion and destination quote exist. The [quote comparison template](quote-comparison-template.json) leaves missing amounts null. The calculator rejects incomplete coverage, mixed-currency totals and unsupported zero-cost lines. Public fee formulas and hypothetical component reductions remain scenarios, not invoices.

## Engineering continuation

1. Obtain comparable complete factory pricing for the baseline and the same-capability alternative, including minimum quantities and supplier-provided harness material. Ask your chosen manufacturer for the same explicit scope and qualification boundaries.
2. Complete the prepared silicone-wire harness definition and verify electrical/mechanical compatibility. Re-source the unchanged analog parts and trace each accepted alternative to its exact datasheet/footprint.
3. Reduce distinct MPNs, bespoke mechanical pieces and costly assembly features only where the resulting circuit, layout and enclosure meet the existing requirements. A lower price has no authority to waive thermal, fault, fit or signal findings.
4. Re-run schematic/pin checks, routing/DFM, analog/power simulations, target firmware build, concurrency/transport checks and enclosure clearance against the actual alternative files. Perform physical signal, thermal, six-hour endurance and fit acceptance on the first article.
5. Compare complete quote totals. If one-third cannot be reached, retain the lowest demonstrated cost passing the same requirements and report its real ratio. Current [qualification status](qualification-status.json) keeps these gates open.

## Evidence and reproduction

- [Tactile materials and harness](tactile/README.md), [source observations](tactile/sources.json).
- [Electronics review](electronics/README.md), [native shared-COM rejection](electronics/shared-com-spice.md).
- [Power and packaging](power-packaging/power-packaging-options-2026-10-23.md), [battery calculation](power-packaging/battery-runtime-calculation.json).
- [Cost calculator](build_cost_review.py), [public assembly fees](assembly-fees.json), [generated arithmetic](cost-review.json).

Run `python3 hardware/glove-v4/value-engineering/build_cost_review.py` from the repository root. It binds the comparison to the current requirement/component hashes and counts physical PCB pads and placement sides. The native simulation runner and compressed waveforms are retained separately; they establish model behavior under documented assumptions, not physical glove measurements.
