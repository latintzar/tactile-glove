# V4 battery harness — Micro-Fit factory variants

## Current factory contract

The selected pack is Jauch `250480 / LI18650JLS HB 1S2P+PCM+FUSE+2 WIRES 70MM`. Its protected pack remains sealed and unmodified. The supplied red and black leads are AWG22 and 70 ±5 mm.

The current battery power interface is a direct Micro-Fit 3.0 path:

- PCB header: Molex `43045-0200`, J12, right-angle 2-circuit through-hole header.
- Pack housing: Molex `43025-0200`, 2-circuit receptacle.
- Pack contacts: two Molex `43030-0007` female tin crimp contacts, one per AWG22 lead.
- Polarity: housing first-circuit mark mates to header circuit 1; circuit 1 is VBAT_ENTRY/red positive and circuit 2 is GND/black negative. Verify the molded rib or “1” identifier at first article.
- J12 pin1 is(4.10,66.25), rotation180°, mating toward+Y. Its locating peg is(4.10,70.57),9.43mm from the80mm PCB edge, within the drawing10.16mm maximum. The audited bare-header height is9.27mm maximum plus0.20mm assembly allowance. The conservative mated profile is11.26mm above the PCB; wire exitY is82.82±0.83mm from the drawing chain, plus±0.20mm assembly allowance. See[mechanical fit](../enclosure/battery-connector-fit.md).
- J13 remains a separate JST PH 2-position connector for the Semitec 103AT-2 thermistor. It does not carry battery power.

Install Littelfuse `045102.5MRL` (451 NANO2, 2.5 A very-fast-acting) in the positive path from VBAT_ENTRY to VBAT, before every board battery branch. The primary datasheet gives 125 V maximum voltage, 28.6 mΩ nominal cold resistance, 1.029 A²s nominal melting I²t, and a 5 s maximum opening time at 200% rating (5 A). The standard 25% continuous derating gives a 1.875 A design point; the revised 1.525 A battery-input load step includes the 190 mΩ path-loss allocation. With an additional 0.85 temperature factor the fuse allocation is 1.594 A. Verify that factor against the current curve and measured local temperature. The fuse is a fault layer, not a 2 A current clamp; first-article testing must measure inrush, thermal rise and fault opening.

Primary source URLs and captured facts are recorded in [battery-path-primary-sources.json](battery-path-primary-sources.json). The Molex drawings identify header circuit 1 on the marked surface and the housing first-circuit rib/“1” identifier. The 43030 contact drawing covers 20–24 AWG and maximum 1.85 mm insulation OD, so the Jauch AWG22 termination is within the specified wire family.

## Wire sizing and acceptance

Copper-only planning for 70 mm of each AWG22 lead uses approximately 52.96 mΩ/m at 20 °C:

```text
R_wire_loop ≈ 2 × 0.070 m × 0.05296 Ω/m = 7.41 mΩ
Vdrop(1.281 A charge corner) ≈ 9.5 mV
P_wire(1.281 A) ≈ 15.6 mW
```

Contact, crimp and temperature contributions are measured on the finished harness; the copper estimate is not a completed-harness guarantee. The 43030-0007 crimp must be made to the supplied AWG22 conductor with the manufacturer tooling/process. Record crimp height or pull acceptance from the factory process, conductor pull, contact retention, loop resistance, insulation, polarity and thermal rise.

Factory acceptance:

1. Inspect the unmodified pack, lead colours, connector key and first-circuit identifiers.
2. Treat the protected pack leads as live whenever they are connected to the pack, even when the PCB is off. Use a voltmeter for polarity/open-circuit voltage and a current-limited controlled-load or charge simulation for voltage-drop checks. Perform continuity, inter-pin isolation and crimp-pull checks on an unpowered dummy AWG22 test harness or disconnected board-side harness only; record circuit 1 red positive and circuit 2 black negative.
3. Measure finished loop resistance and voltage drop at 1.281 A current-limited charge simulation; retain contact/crimp measurements.
4. Apply the 1.525 A battery-input load step and record connector, fuse and wire temperature. Test charge, startup, recording and low-voltage transitions.
5. Test a controlled fault fixture for the 045102.5MRL timing and inspect the PCB connector, copper and pack lead after opening. Do not short the live pack.
6. Measure the usable lead length after crimp consumption. Choose the direct or factory-extension route below, inspect the accepted pack-exit datum, fixture the R4 bends and retain3mm strain-relief slack. Record pull, insulation, thermal and route acceptance before closing the enclosure.

## Direct and extended variants

Both use the same Molex header, housing and two contacts. The direct variant uses the original AWG22 pack leads; accept it when measured usable length after crimp exceeds the selected54.668–61.509mm external route by at least3mm.

The **factory-extension fallback** adds one35mm AWG22 conductor piece to each original lead, with5mm overlapping joints. Each lead gains30mm effective reach. Count two added pieces,70mm new conductor total, two joints at≤2mΩ each and60mm total effective gain. A65mm shortest stock lead becomes95mm before terminal consumption. Reserve14.25mm as a conservative upper bound for the terminal/housing portion and3mm slack: the74.174mm maximum external route retains3.576mm margin. The actual fitted terminal consumption is measured. These variants are alternative assemblies.

The CAD carries two completeR4 fallback paths and their straightØ4×16mm sleeve envelopes centered at(6.5,63,14) and(10.5,67,17). Full geometry and analytic arc lengths are in[the harness export](../enclosure/harness-envelopes.json). The factory path family spans62.274–74.174mm across the audited connector exit-height range31.525–40.935mm. Pack exitY49–51,Z13.5mm with0.20mm route-axis allowance is the receiving/assembly region; Jauch's drawing leaves that exit coordinate undimensioned.

Use a qualified5mm overlapping AWG22 joint with aTE Raychem ATUM-3/1-0-STK adhesive-lined sleeve cut16mm (accept recovered length14–16mm), finishedOD≤4mm. The assembler specifies and accepts solder/crimp process, wire and sleeve material, live-pack handling, pull and thermal qualification. Retain each stiff sleeve with an adhesive textile strain-relief tab on insulating padding; R4 bends begin beyond sleeve ends. The new joints preserve the AWG22 conductor size; the older AWG24 PH adapter remains historical only.

The190mΩ source-path allocation now includes70mm added conductor and≤4mΩ total joint resistance. Use the linked[battery protection review](battery-path-protection-review.md) and current power results for full-path arithmetic; the copper-only estimate above describes the original direct leads. Record finished-harness resistance rather than substituting that estimate for measurement.
