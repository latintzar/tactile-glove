# Closed-cuff thermal screening

**The present design has a thermal qualification gap.** External surface area can reject the recording load at room temperature, but the internal battery/PCB gaps and the wrist contact path are unmeasured. The sensitivity cases cross pack and contact targets. Sustained recording at 35–40 °C ambient needs a verified thermal path and operating envelope before wearable release.

This is an executable five-node, steady-state thermal-resistance calculation, not FEA, CFD, a six-hour transient simulation, or proof of actual temperatures. It screens the frozen 112 × 104 × 45.5 mm case and 112 × 105.6 × 47.1 mm assembly. CAD, components and routing are unchanged.

## Heat generation

| Mode | Electronics heat, W | Internal pack heat, W | Charge current, A |
|---|---:|---:|---:|
| Recording, duty budget | 2.44–2.44 | 0.02–0.19 | discharging |
| Recording, sustained budget | 3.11–3.11 | 0.03–0.24 | discharging |
| Charging, acquisition off | 0.75–2.03 | 0.03–0.35 | 0.96–1.28 |
| Charging + duty recording | 2.94–3.73 | 0.01–0.28 | 0.55–1.10 |
| Charging + sustained recording | 3.51–4.28 | 0.01–0.23 | 0.41–0.93 |
| USB, charge inhibited, acquisition off | 0.15–0.61 | 0.00–0.00 | 0.00–0.00 |
| USB, charge inhibited, duty recording | 2.53–2.80 | 0.00–0.00 | 0.00–0.00 |
| USB, charge inhibited, sustained recording | 3.19–3.54 | 0.00–0.00 | 0.00–0.00 |

Recording starts with the authored [energy budget](../energy-budget.json): 2.440 W duty or 3.110 W sustained at pack output, including main-converter and 190 mΩ external-path losses. All output is assigned as assembly heat, without credit for escaped RF or the external hand tile. Extra cell/PCM heating uses an **unmeasured** 0.03–0.15 Ω internal-resistance sensitivity plus 0–0.10 W entropic allowance. The 20% energy reserve is capacity headroom, not a heat source.

The BQ25616 is a switching NVDC charger. The model subtracts energy stored in the battery from USB input, applies the actual 1.146–1.348 A USB limit and 1.139–1.281 A charge setting, and solves charge-current reduction under simultaneous load. It sweeps buck-stage efficiency 85–94%, while accounting for battery-path losses separately. Acquisition-off output of 0.10–0.40 W is a measurement assumption. USB is fixed at nominal 5 V; source/cable voltage extremes remain a test condition. The [TI datasheet](https://www.ti.com/lit/ds/symlink/bq25616.pdf) provides topology and a typical efficiency example, not a guarantee for this assembly.

## Temperature sensitivity

The table uses a **defined 34 °C wrist phantom with 15 K/W effective contact resistance**, including textile/contact/body-side resistance. It is a reproducible comparison boundary, not a validated human model. Ranges combine electrical and heat-transfer corners; independent heat extrema remove electrical correlations conservatively. Node temperatures are averages, with local hot spots unresolved.

| Mode | Ambient, °C | Exposed shell, °C | Pack, °C | Wrist-facing base, °C |
|---|---:|---:|---:|---:|
| Recording, duty budget | 25 | 29.3–34.1 | 39.1–51.6 | 38.8–46.0 |
| Recording, duty budget | 35 | 38.7–42.5 | 45.1–56.5 | 43.3–48.9 |
| Recording, duty budget | 40 | 43.4–46.7 | 48.3–59.0 | 45.6–50.5 |
| Recording, sustained budget | 25 | 30.4–36.2 | 42.0–57.4 | 41.3–50.0 |
| Recording, sustained budget | 35 | 39.7–44.5 | 48.0–62.2 | 45.7–52.9 |
| Recording, sustained budget | 40 | 44.4–48.7 | 51.1–64.7 | 48.0–54.4 |
| Charging, acquisition off | 25 | 26.7–33.3 | 31.5–51.3 | 32.6–45.1 |
| Charging, acquisition off | 35 | 36.1–41.7 | 38.1–56.2 | 37.3–48.0 |
| Charging, acquisition off | 40 | 40.8–46.0 | 41.3–58.8 | 39.4–49.6 |
| Charging + sustained recording | 25 | 31.0–39.6 | 43.5–65.5 | 42.6–56.0 |
| Charging + sustained recording | 35 | 40.3–47.8 | 49.5–70.1 | 47.0–58.9 |
| Charging + sustained recording | 40 | 44.9–51.9 | 52.5–72.5 | 49.3–60.3 |

**Charging rows show requested-power equilibrium before temperature control.** In the hardware, the NTC/CE circuit inhibits charging at 39.01–41.23 °C. The high equilibrium numbers indicate likely interruption or cycling, not uninterrupted real charging at those temperatures. USB power to SYS continues after inhibition; the explicit charge-inhibited cases in [results.json](results.json) retain that heat. At 40 °C ambient the charge-enable window itself leaves almost no thermal headroom. NTC bonding, cell-to-NTC gradient and response lag still determine protection performance.

The [selected Jauch pack](https://www.jauch.com/downloadfile/61f0fb7230945444b292c0fac704609f8/6700%20mAh,%20LI18650JLS%20HB%201s2p,%20Mat.%20250480.pdf) specifies 10–45 °C for charging and −20–60 °C for discharge. This screen proposes a 40 °C sustained-contact goal and 43 °C fixture stop. These are engineering acceptance proposals, not a glove certification: [NASA contact guidance](https://www.nasa.gov/reference/9-0-hardware-and-equipment-vol-2/) treats 43 °C skin temperature as a relevant pain/performance threshold and requires contact-duration/material analysis. Base temperature is a contact-surface proxy.

The JSON also includes all-face bench cooling and an insulated-base stress boundary with zero wearer cooling. At 25 °C, that insulated-base sustained case reaches 48.6–82.3 °C at the base. It deliberately exposes reliance on body/contact heat removal; the upper values are extrapolated steady stress solutions, not expected normal-use temperatures. Neither boundary is a guaranteed bound on a worn product.

## Passive heat paths

Top/sides expose 0.03044 m²; the base has 0.01156 m². The projecting window/carrier receive no extra-area credit. The model separates PCB, pack, exposed shell, base and internal air. It uses PCB Z29–30.6 mm, lid underside 44.2 mm, pack top 24 mm, 1.3 mm floor and 1.7 mm foam over 0.00249 m². The pack clearance box approximates the two-cylinder pack surface.

| Path or parameter | Screening assumption |
|---|---|
| PCB → lid | 13.6 mm stagnant-air gap and radiation, then 1.3 mm nylon |
| PCB → pack | 5 mm stagnant-air gap and radiation |
| PCB → base outside pack | 27.7 mm gap and radiation, then nylon |
| Pack → sides | 20 mm representative gap and radiation, then nylon |
| Pack → base | Actual foam area/thickness in series with nylon floor |
| Shell → base | Nylon sidewall conduction; no isothermal metal-case assumption |
| Additional internal mixing | Separate air node; 0.1–3 W/(m² K) beyond stagnant-gap paths |
| Outside natural convection | 3–8 W/(m² K), still-air/orientation sensitivity |
| Radiation | Nonlinear Stefan–Boltzmann; outer emissivity 0.75–0.95, internal effective emissivity/view factor 0.45–0.85 |
| PA12 / foam conductivity | 0.127–0.30 / 0.03–0.10 W/(m K), unqualified material ranges |

The heat-transfer ranges are sensitivities, not statistical intervals or manufacturer maxima. [NASA’s thermal guide, p.43](https://ntrs.nasa.gov/api/citations/20220006584/downloads/NASAPassiveThermalGuidebookv5%201Public.pdf) places Earth natural convection near 5 W/(m² K); [NIST](https://www.nist.gov/el/fire-research-division-73300/firegov-fire-service/fire-dynamics) gives representative air conductivity 0.026 W/(m K). [EOS PA2200, p.1](https://www.protiq.com/out/marketplace/merchants/0dab15bdac1ae142211675f47bd25f37/datasheets/13_pa2200_product_information_07-2020_en.pdf) provides a PA12 analogy, not the selected HP MJF property. [Rogers HT-800, p.2](https://www.sealanddesign.com/wp-content/uploads/2019/03/BISCO-HT-800.pdf) provides a 0.09 W/(m K) foam example; production foam is still unspecified.

The current design specifies no intentional board-to-exterior thermal contact. The model omits detailed copper/thermal vias, nylon ribs, fastener/wire conduction, adhesive contacts and spatial spreading. These can redistribute heat in either direction. The exposed shell node is also an average; nylon does not guarantee uniform surface temperature. BQ25616’s 110 °C typical junction regulation and 31.9 K/W JEDEC junction-to-ambient value cannot prove installed junction temperature.

## Heat-rejection requirement

An independent outside-only check holds every exposed top/side surface at 40 °C, with the base insulated. This is optimistic because it omits internal temperature drops:

| Ambient, °C | Heat rejected at 40 °C, W |
|---|---:|
| 25 | 3.59–6.46 |
| 35 | 1.23–2.20 |
| 40 | 0.00–0.00 |

At 35 °C, sustaining the current workload while keeping all those surfaces at 40 °C needs another **0.94–2.12 W** of heat removal through a verified boundary, or that amount of heat-load reduction. At 40 °C ambient, passive air cooling has zero capacity at a 40 °C surface. Improving an internal heat spreader alone cannot remove this external heat-rejection constraint.

**Engineering disposition:** preserve the current prototype for instrumented bench/phantom characterization. Thermal release requires measured operating limits. If cell temperatures or contact targets fail at the intended ambient/workload, revise the heat path toward the outward shell while limiting the wrist path, and/or reduce workload or charging current. Any spreader must preserve the RF keepout and electrical insulation; no geometry for such a change has been selected or installed. Simultaneous charging and recording remains a qualification case, not an approved wearable use claim.

## Physical acceptance test

1. Instrument both cells, NTC bond, PCM region, charger/adjacent PCB, TPS63070/inductor, ESP module, SD card, inner/outer floor, actual textile contact, lid and ambient. Use bonded thin thermocouples and calibrated IR; record 1 Hz temperatures, battery/USB/rail V/I, CE/status, frame rate and dropped frames.
2. Test the fully closed final stack at 25/35/40 °C in still air ≤0.1 m/s and intended orientations. Compare all-face bench with actual strap/textile on a characterized warm wrist phantom. Specify contact resistance, pressure and phantom temperature; include a hotter-skin sensitivity. Human wear follows fixture acceptance.
3. Run actual maximum supported continuous camera/tactile/dual-IMU/SD/radio workload for six hours, including low battery. Test acquisition-off charge from low SOC through CC/CV termination, then simultaneous recording/charging at low/mid/high SOC on a ≥1.5 A Type-C source, including voltage/cable extremes. Record input limiting and thermal cycles.
4. Continue plateaus until all monitored temperatures change <0.2 °C per 10 minutes for 30 minutes, or a stop limit. Record full warmup/cooldown to determine thermal capacitance and NTC delay. Verify cell ≤45 °C during charging, ≤60 °C during discharge and measured charge cutoff/gradient/lag margin.
5. Stop at 43 °C contact, 45 °C charging cell, 60 °C discharging cell, or the applicable component limit. Validate recording after CE inhibition. Repeat with final foam, seal, adhesives and strap tension after thermal cycling; publish the measured ambient/workload envelope or revise the design.

## Reproduction

Run `python3 hardware/glove-v4/verification/thermal-screen/screen.py`. [sources.json](sources.json) separates primary facts from assumptions. [results.json](results.json) exports source/script hashes, electrical ranges, every boundary case and maximizing corners. The standard-library solver checks energy conservation, zero-load equilibrium and monotonic heating. It models no warmup/cutoff timing, human perfusion, direct sun or local semiconductor junctions.

Validation: 408 electrical scenarios; 18432 thermal corner solutions; maximum steady energy residual 1.1e-10 W.
