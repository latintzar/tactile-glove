# Battery-path protection review

Review date: 2026-10-22. Scope: Jauch 250480 1S pack, 3.2–4.2 V, 1.281 A maximum charge, 1.292 A peak scenario discharge and a 1.525 A converter load step including path loss, and the existing BQ25616 battery path.

## Decision

The earlier LTC4368-1 proposal was rejected even before the additional battery-path losses below were included. Its comparator corners leave no resistor window that both passes the legitimate 1.387 A battery input step and guarantees a trip below 2 A:

```
R < 40 mV / 1.387 A = 28.84 mΩ  (pass the load-step at minimum threshold)
R > 60 mV / 2.000 A = 30.00 mΩ  (guarantee the maximum threshold below 2 A)
```

A 2 A fuse also cannot be described as a 2 A clamp; at 1.117× rating it may continue operating. The recommended minimal manufacturable change is therefore a higher-rated direct-AWG22 connector plus a lower fast fuse:

* PCB header: **Molex 43045-0200**, Micro-Fit 3.0, 2-circuit, right-angle, through-hole, snap-in plastic PCB lock, tin finish.
* Pack-side housing: **Molex 43025-0200**, 2-circuit receptacle housing.
* Pack contacts: **2× Molex 43030-0007**, tin female crimp contacts for 20/22/24 AWG.
* Positive-path fuse: **Littelfuse 045102.5MRL**, 2.5 A, 451 NANO2 very-fast-acting, 125 V, 28.6 mΩ nominal cold resistance.

This removes the AWG22→AWG24 adapter and keeps the battery charging path passive and bidirectional. It requires a PCB footprint/routing change and connector-envelope check; it does not require the LTC4368 IC, MOSFETs, sense resistor, or their charge-voltage drop.

## Current and fault coordination

Molex's primary Micro-Fit specification gives the 2-circuit, 22-AWG reference values as 5.5 A wire-to-wire and 6 A wire-to-board, based on a 30 °C maximum temperature rise. The 43045 header is the board-to-wire member of the 43045/43025 family. The 43030-0007 contact is explicitly 20–24 AWG and is listed at 7 A maximum per contact; the derating table is the controlling value for this two-circuit assembly. [Molex PS-43045-001, current table and curves, pages 8–10](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/430/43045/PS-43045-001.pdf), [43045-0200 manufacturer listing](https://www.molex.com/en-us/products/series-chart/43045), [43025-0200 manufacturer listing](https://www.molex.com/en-us/products/series-chart/43025), [43030-0007 manufacturer listing](https://www.molex.com/en-us/products/part-detail/43030-0007)

The 2.5 A fuse's standard 25% continuous derating gives a 1.875 A continuous design point. Including the 190 mΩ path-loss allocation raises the 1 A system-load step to 1.525 A at the battery. Applying an additional 0.85 temperature factor leaves a 1.594 A continuous fuse allocation. The current curve and measured local ambient must support this allocation. At 200% rating (5 A), Littelfuse specifies a maximum opening time of 5 s; its 2.5 A electrical table gives 1.029 A²s nominal melting I²t and 28.6 mΩ nominal cold resistance. Five amperes remains below the connector's 5.5 A conservative wire-to-wire reference and 6 A wire-to-board reference. The pack AWG22 lead and the actual PCB copper still require a thermal test at 5 A until fuse opening. [Littelfuse 451/453 datasheet, pages 1–3](https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1)

Place the fuse immediately at the battery-entry positive path, before any board branch. The pack PCM and 7 A pack fuse remain upstream backup protection. The external fuse is the local partial-fault layer; it is not an instantaneous 2 A current limiter.

## Availability snapshot

DigiKey showed 14,547 of 43045-0200, 145,783 of 43025-0200, and 667,524 of 43030-0007 when checked. Mouser showed 5,227 of 045102.5MRL. These are distributor snapshots, not a Bulgaria delivery promise. [DigiKey 43045-0200](https://www.digikey.com/en/products/detail/molex/0430450200/252526), [DigiKey 43025-0200](https://www.digikey.com/en/products/detail/molex/0430250200/252496), [DigiKey 43030-0007](https://www.digikey.com/en/products/detail/molex/0430300007/252479), [Mouser 045102.5MRL](https://www.mouser.com/ProductDetail/Littelfuse/045102.5MRL?qs=8QfiMw8FY5Nvmzv26%252BPRjA%3D%3D)

The connector/fuse set remains quote-only pending PCB footprint routing, mating and keying inspection, pack-lead thermal testing, fuse fault timing, inrush behavior, and charge termination validation. The current V4 source records now carry the direct Micro-Fit choice; physical acceptance and release remain open.

Updated executable checks: [battery-path-check-results.json](../power/battery-path-check-results.json). Nine topology/algebra/allocation checks pass; pulse, thermal and first-article endurance evidence remains outstanding.

The direct pack termination remains preferred. If its measured finished reach fails the enclosure gauge, the documented factory extension may add up to35mm of AWG22 wire per lead, with each splice accepted at≤2mΩ by a Kelvin measurement on an unpowered harness fixture. Counting the full added conductor length at65°C gives a total path subtotal of approximately189.912mΩ, inside the same190mΩ assembly allocation. Every completed power path must still pass the aggregate voltage-drop test. This is an assembly acceptance budget, not a guaranteed solder-joint resistance.

The +35 mm conductor per lead uses a 5 mm overlap and adds 30 mm effective reach. The mechanical route must include the staggered insulated splice sleeves; this length is not a free-space straight-line estimate. The electrical subtotal retains the full added conductor length at 65 °C.
