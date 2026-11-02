# V4 supplier assembly scope

**Quote status:** unpriced integration scope for the current V4 routing work. The supplier delivers a tested cuff kit; the user laminates the prepared tactile cells onto the glove and plugs the keyed kit. Record the actual part revisions, firmware hash, serial, and first-article photos with the shipment.

## Supplier deliverables

| Qty | Deliverable | Acceptance record |
|---:|---|---|
| 1 | Populated V4 cuff PCB: six tactile sockets J5–J10, camera FFC J14/J_CAM, remote hand-tile connector J15, microSD J16, button SW2, RGB D22, and soldered cuff IMU U61 | Assembly inspection, connector pin-1 marks, camera-tail orientation check, board serial |
| 6 | Keyed tactile harnesses: thumb J5, index J6, middle J7, ring J8, little J9, palm/heel J10 | Label each branch; pin-to-pin continuity and adjacent isolation; retain wiring sheet |
| 1 | Remote dorsal-hand IMU tile: U1/U_IMU_HAND, tile connector J1, arrow toward middle finger | Address `0x6B`; tile inspection; J1-to-J15 cable continuity |
| 1 | 100 mm keyed JST-SH hand-tile cable | Pin 1 through 4 continuity: GND, 3V3_SYS, I2C_SDA, I2C_SCL |
| 20 | PVDF lead-prep subassemblies, one per tactile location | Cut 10 × 14 mm blank; two silver-tab leads attached and strain-relieved; signal face marked; tab gap visible |
| 20 sets | Tactile laminate cut kit: pressure electrode pairs, isolated Velostat/Linqstat islands, separators, PVDF subassemblies, and covers | IDs I1–I3, M1–M3, R1–R3, L1–L3, T1–T2, P1–P4, H1–H2; materials batch recorded |
| 1 | Cuff integration: camera FPC, microSD, protected battery, and cuff cover fitted for the first article | FPC contact side and pin 1 recorded; card latch, battery dimensions/leads, cover clearance, and first-power record |
| 1 | Factory battery harness: crimp the unmodified Jauch AWG22 red/black leads directly into two `43030-0007` contacts, house in `43025-0200`, and mate PCB `43045-0200`; install `045102.5MRL` in the positive entry path | Pin 1 +/red and pin 2 −/black; direct crimp pull/continuity/polarity and 70 ±5 mm final route recorded; J13 remains the separate PH thermistor |
| 1 | Factory firmware load and bench test | Firmware version/hash recorded; USB enumeration, button timing, RGB states, both IMU identities, and branch continuity recorded |

## User assembly after delivery

1. Laminate the 20 identified tactile stacks onto the glove using the [V3 cut template and cross-section](../../glove-v3/sensors/cross-section.svg). Keep each marked PVDF signal face toward the contact side.
2. Route each four-wire bundle along the side/back with the specified bridge and slack loop.
3. Plug the six named keyed branches into J5–J10 and plug the hand-tile cable between J15 and J1.

The supplier completes camera FPC, microSD, protected-battery integration through the specified Micro-Fit harness, cover, and first-power integration. The packaged cell stays unmodified; its AWG22 leads use the direct or dimensioned factory-extension variant, with keyed Micro-Fit termination and recorded reach/resistance acceptance. Use the [factory flash/test/onboarding procedure](factory-flash-and-acceptance.md) and its serial-linked record. The selected battery is Jauch250480 protected6.5Ah minimum;the exact camera tail,final enclosure fit and measured six-hour runtime remain engineering acceptance checkpoints.
