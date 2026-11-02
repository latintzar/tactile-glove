# V4 glove handoff and assembly guide

This guide connects the V4 cuff board to the existing 20-cell tactile glove and the separate dorsal-hand IMU tile. The factory prepares the populated board and keyed harnesses. The wearer-side build fits the soft sensor laminate, routes each branch, seats the hand tile, and verifies the camera and controls.

**Current engineering status:** V4 main routing is ongoing. The selected Jauch250480 protected6.5Ah pack gives a6.019h conservative energy scenario;actual six-hour endurance,temperature and storage margin require first-article measurement. This guide is a physical handoff for the integration work; it is not a manufacturing release.

Use the [factory flashing,acceptance and phone onboarding handoff](factory-flash-and-acceptance.md) for the supplied firmware and exact camera/battery checks.

Open the [visual assembly guide](assembly.html) for the dataflow diagram, progressive steps, harness cards, and photo checkpoints.

## System contract

The right-hand glove carries 20 pressure taxels at 50 Hz and 20 PVDF vibration channels at 4 kHz per channel. The cuff camera is CamThink `73.002.000035`, an OV5640 module with 120° optics and 8 cm preset fixed focus. Two ISM330DHCXTR devices run at 833 Hz, ±4 g and ±1000 dps over 400 kHz I²C: the cuff camera IMU is address `0x6A`, and the dorsal-hand IMU is address `0x6B`.

The cuff has one large top button, a diffused common-anode RGB indicator, USB-C, Wi-Fi/Bluetooth, and a controlled microSD socket. The six tactile branches are keyed GHS connectors on the cuff board: thumb, index, middle, ring, little, and palm/heel.

## Who does what

### Supplier prepares

- Populate and inspect the V4 cuff PCB, including the soldered cuff IMU `U61` at the camera seat, six keyed tactile sockets, camera FFC socket `J_CAM`, remote hand-tile connector `J15`, and microSD socket `J_SD`.
- Build and label the six tactile branch harnesses. Mark each plug's pin 1 and branch name; verify conductor continuity pin-to-pin and adjacent isolation with the harness disconnected.
- Fit the camera FFC only after the supplied module tail has been checked for contact side and pin 1. The contract uses the bottom-contact 24-way `FH12-24S-0.5SH(55)` socket.
- Prepare the cuff camera seat, battery restraint, RGB light pipe or diffuser, and button cap so the single top actuator reaches `SW2` without side load. The factory crimps the unmodified AWG22 battery leads directly into Molex 43030-0007 contacts, houses them in 43025-0200 and mates PCB 43045-0200; the wearer receives the keyed connector.
- Record first-article photos and electrical checks in the build record.

### User or integrator performs

- Cut and laminate the 20 soft locations using the existing V3 template and cross-section.
- Mark each PVDF pair's signal face, keep that face consistent, and route the two PVDF leads with the two pressure leads toward the correct branch.
- Plug the six keyed branches into their named cuff sockets, then install the dorsal-hand tile over the third metacarpal with its arrow toward the middle finger and its plug toward the wrist.
- Route the hand IMU cable above the back of the wrist with a shallow S loop. Fasten the cable jacket 8 mm behind each plug and keep it separated from the high-impedance PVDF leads.
- Hand the plugged glove kit to the supplier for camera FPC, microSD, protected battery, cover, and first-power integration checks.

## Sensor laminate and PVDF direction

Use the existing V3 starting files: [cut template](../../glove-v3/sensors/cut-template.svg), [cross-section](../../glove-v3/sensors/cross-section.svg), [sensor assembly](../../glove-v3/sensors/assembly.md), and [connector wiring CSV](../../glove-v3/sensors/wiring.csv).

For each location, the stack from glove fabric toward the contact/outside surface is: lower pressure electrode, Velostat/Linqstat island, upper pressure electrode, continuous electrical separator, PVDF sheet, and insulating cover. The PVDF face connected to the vibration input faces outward toward the contact side. Keep the two staggered PVDF tab joints on opposite ends and leave a visible insulating gap around the film edge. Anchor the four-wire bundle 15–20 mm behind the cell and leave a 12–15 mm side/back slack loop clear of creases.

There are 20 locations: I1–I3 index, M1–M3 middle, R1–R3 ring, L1–L3 little, T1–T2 thumb, P1–P4 palm below the knuckles, and H1–H2 heel/base of palm. The starting active footprint is 8 × 10 mm inside a 10 × 14 mm PVDF blank. Fit paper coupons to the actual glove before cutting film.

## Six keyed tactile branches

All six plugs are keyed. Align the latch and the board pin-1 mark, press evenly, and let the key guide insertion. The wire colour is an inspection aid; the factory continuity check is authoritative.

| Branch / cuff ref | Connector | Cell locations | Signal pins | Shared pins |
|---|---|---|---|---|
| Thumb / `J_THUMB` (`J5`) | `BM06B-GHS-TBT` · 6-way | T1, T2 | 1 PVDF_T1, 2 PRESS_T1, 3 PVDF_T2, 4 PRESS_T2 | 5 `VEXC2V5`, 6 `GND` |
| Index / `J_INDEX` (`J6`) | `BM08B-GHS-TBT` · 8-way | I1–I3 | 1/2 I1, 3/4 I2, 5/6 I3 PVDF/pressure pairs | 7 `VEXC2V5`, 8 `GND` |
| Middle / `J_MIDDLE` (`J7`) | `BM08B-GHS-TBT` · 8-way | M1–M3 | 1/2 M1, 3/4 M2, 5/6 M3 PVDF/pressure pairs | 7 `VEXC2V5`, 8 `GND` |
| Ring / `J_RING` (`J8`) | `BM08B-GHS-TBT` · 8-way | R1–R3 | 1/2 R1, 3/4 R2, 5/6 R3 PVDF/pressure pairs | 7 `VEXC2V5`, 8 `GND` |
| Little / `J_LITTLE` (`J9`) | `BM08B-GHS-TBT` · 8-way | L1–L3 | 1/2 L1, 3/4 L2, 5/6 L3 PVDF/pressure pairs | 7 `VEXC2V5`, 8 `GND` |
| Palm/heel / `J_PALM_HEEL` (`J10`) | `BM14B-GHS-TBT` · 14-way | P1–P4, H1–H2 | 1/2 P1, 3/4 P2, 5/6 P3, 7/8 P4, 9/10 H1, 11/12 H2 PVDF/pressure pairs | 13 `VEXC2V5`, 14 `GND` |

At each cell, the pressure lower contacts join the branch `VEXC2V5` return and the PVDF bottom faces join the branch `GND` return. Keep pressure signals and PVDF signals in their named pairs through the branch breakout.

## Cuff, hand tile, camera, and storage

The cuff IMU `U61` is soldered to the main cuff PCB at the camera seat, address `0x6A`. `J15` is the external keyed 4-way connector for the remote hand tile; it mates to tile connector `J1`, where `U_IMU_HAND` is address `0x6B`. Pin 1 is `GND`, pin 2 `3V3_SYS`, pin 3 `I2C_SDA`, and pin 4 `I2C_SCL`. The tile arrow points toward the middle finger and its connector faces the wrist. The 100 mm JST SH cable uses black `GND`, red `3V3_SYS`, blue `I2C_SDA`, and yellow `I2C_SCL` as a visual aid, with continuity checked pin-to-pin.

The selected camera is a CamThink `73.002.000035` OV5640 module with separate `CAM_AVDD_2V8`, `CAM_DVDD_1V5`, and `CAM_DOVDD_1V8` rails. `J_CAM` is a 24-contact bottom-contact 0.5 mm FFC socket with 0.3 mm cable thickness. Seat the lens toward the near-finger view, keep the FPC bend outside the lens seat, and photograph the module tail contact side and pin 1 before locking the latch. The [manufacturer variation and price are verified](../procurement/camera-sourcing.md); receiving inspection of the supplied tail drawing and contact side remains an integration step.

`J_SD` (`J16`) is the Hirose DM3AT-SF-PEJM5 push-push microSD socket with independent card detect. The card is inserted label side according to the socket marking; the spring latch should click and release cleanly. The controlled `SD_VDD` rail is enabled by the controller, and the current card-current limit remains a design assumption pending characterization.

## Button and RGB check

`SW2` (`PTS636SK43SMTR-LFS`) is the single large top button. It is active low on controller GPIO 2. Hold for 800 ms and release to wake; continue to 3 s for pairing; while running, hold for 1.5 s and release to sleep. The common-anode `D22` (`APTF1616LSEEZGKQBKC`) uses active-low red, green, and blue channels. The current indicator language is blue for startup/pairing, green for ready/collecting, amber for low or unqualified battery, and red double flash for ADC trouble.

## First article sequence

1. Photograph the glove flat with all 20 location IDs visible. Photograph each laminate before the cover is applied, including the PVDF face mark and scale.
2. With the cuff unpowered, verify each branch pin map against the table and record pin-to-pin continuity and adjacent isolation.
3. Plug the six branches into their named sockets. Leave the latch and pin-1 marks visible in the harness photo.
4. Install the remote hand IMU cable and hand tile. Confirm the hand arrow points toward the middle finger and the wrist cable has its shallow S loop.
5. Photograph the camera tail contact side, insert the FPC, and record the lens direction. Insert the microSD card and record its label and serial if available.
6. With the board unpowered, inspect the factory Micro-Fit harness: red is pin 1 (+), black is pin 2 (−), and direct crimp pull/continuity/polarity and the 70 ±5 mm route are recorded. Connect the protected battery, check for an unqualified-power indication, then perform the button timing check and observe the RGB state transitions.
7. Run the host preview and record one short USB session plus the two IMU identities. Retain raw data, frame flags, and the first-article photos with the serial number.

## Photo checkpoints

| Checkpoint | Frame the photo around | Acceptance detail |
|---|---|---|
| Sensor stack | One cell, scale, PVDF face mark, wire exit | PVDF signal face outward; tabs separated; lead bridge outside the crease |
| Six branches | Cuff edge, each keyed plug, pin-1 mark, branch label | J5–J10 names visible; no force or crossed branches |
| Hand IMU | Tile top, arrow, wrist plug, cable loop | Arrow toward middle finger; plug toward wrist; cable clear of PVDF |
| Camera | Module tail, FPC contact side, latch, lens direction | Bottom-contact assumption and pin 1 verified against supplied tail drawing |
| Cuff controls | Button cap, RGB diffuser, USB-C, microSD | Button reaches full travel; RGB is visible; card latch is seated |
| First power | Cuff, cable, RGB state, host preview timestamp | State transition and both IMU IDs recorded with serial |

## Contract files

- [V4 system contract](../system-contract.json)
- [V4 camera interface](../interfaces/camera-interface.json)
- [V4 IMU interface](../interfaces/imu-interface.json)
- [V4 microSD interface](../interfaces/sd-interface.json)
- [V4 power firmware contract](../power/firmware-contract.json)
- [V4 energy budget](../verification/energy-budget.md)
- [V3 tactile assembly evidence](../../glove-v3/sensors/assembly.md)
