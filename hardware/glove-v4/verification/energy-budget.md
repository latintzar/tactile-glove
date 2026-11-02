# V4 continuous-recording energy budget

The selected pack is **Jauch 250480, LI18650JLS HB 1S2P**, factory assembled with PCM and a 7 A fuse. Its minimum capacity is 6,500 mAh at 3.6 V (23.4 Wh). Nominal size is 69 × 38 × 20 mm and mass 100 g; the enclosure uses the drawing tolerances plus installation clearance. Its AWG22 red/black leads remain part of the unmodified pack. The factory harness uses direct Molex Micro-Fit 3.0: PCB header **43045-0200**, pack housing **43025-0200**, and two **43030-0007** contacts terminating the AWG22 red/black pack-lead harness. Pin 1 is positive/red and pin 2 is negative/black; a separate Semitec 103AT-2 measures pack temperature through J13. The positive entry path includes Littelfuse **045102.5MRL**, 2.5 A fast fuse, before every board battery branch. Final J12 placement and 70 ±5 mm lead reach are first-article mechanical checks. [Manufacturer datasheet](https://www.jauch.com/downloadfile/61f0fb7230945444b292c0fac704609f8/6700%20mAh,%20LI18650JLS%20HB%201s2p,%20Mat.%20250480.pdf).

The factory measures finished reach before selecting the direct-lead or specified extension variant. The fallback adds 35 mm AWG22 per lead with a 5 mm overlap, retaining 30 mm effective reach per lead; its two insulated joints and full added conductor length are included in the 190 mΩ energy loss allocation. The sealed protected pack remains intact. Crimp, polarity, resistance, thermal and exact routed-length acceptance are specified in the [battery harness drawing and procedure](../procurement/battery-harness.md).

This replaces the 4.8 Ah LP735977JH candidate. The circuit charges at 1.205 A nominal, at most 1.28 A over the documented resistor/controller corners, below the pack's 2 A limit. Charging uses the pack's 10–45°C interval. Capture stops at 3.2 V and restarts above 3.55 V, measured on the board’s `VBAT` node after the connector and fuse; the latter is restart hysteresis, not the operating discharge cutoff.

## Camera and load inputs

The circuit uses **AVDD 2.8 V, external DVDD 1.5 V and DOVDD 1.8 V**. Two **SN74AXC8T245PWR** translators connect the 1.8 V camera to the 3.416 V controller. SN74AVC8T245 is not pin-compatible and is not a substitute. The exact topology is in [camera-interface.json](../interfaces/camera-interface.json), checked against the [module specification](https://wiki.camthink.ai/docs/hardware-dev-resources/camera-module-ov5640/) and [AXC datasheet](https://www.ti.com/lit/ds/symlink/sn74axc8t245.pdf).

The camera budget sums AVDD 40 mA, external DVDD 125 mA and DOVDD 12 mA into 177 mA of LDO input current. It claims no saving from the 10 fps setting. The firmware programs 24 MHz XCLK, HTS 2060 and VTS 2622 for nominal 9.99756 fps, VGA JPEG quality 12; timestamps and dropped frames are retained.

Other allowances are 64.405 mA for the analog chain, 3 mA for two ISM330DHCX devices, and 30 mA for translators and remaining board loads. The ESP32 published 286 mA Wi-Fi TX operating point is used continuously in the conservative scenario; this is not a guaranteed maximum of every concurrent CPU/radio workload. The lower-duty scenario is explicitly an estimate.

The selected Kingston SDCIT2 card runs on SPI at 20 MHz. Its published datasheet does **not** specify the current values needed here. **100 mA average and 300 mA peak are design assumptions**, to be checked on the actual selected card. [Kingston datasheet](https://www.kingston.com/datasheets/sdcit2_en.pdf).

## Calculation

The model applies a 20% capacity allowance, 80% converter efficiency, and external battery-path loss separately. Loads are priced at 3.55 V. The path has a 190 mΩ measured-acceptance allocation for pack leads, connector/crimps, fuse, charger BATFET and PCB copper. Loss is evaluated at a 3.2 V protected-pack output throughout the entire run, a conservative scenario. That source node is upstream of the external path; it is distinct from the firmware’s post-fuse `VBAT` measurement and can be below the normal source voltage at capture shutdown. The current is solved from P = (V − I·R)·I; resistive loss is I²R. The 190 mΩ allocation includes thermal and aging allowances that require verification on the assembled unit; it is not a component-guaranteed total.

| Scenario | System current | System power at 3.55 V | Calculated duration |
|---|---:|---:|---:|
| conservative sustained design | 660.405mA | 2.344W | 6.019h |
| realistic duty budget | 525.030mA | 1.864W | 7.671h |
| peak converter sizing | 860.405mA | 3.054W | 4.527h |

Peak-converter sizing is a transient sizing case, not a sustained-runtime claim. The conservative sustained scenario has only 0.019 h (1.16 minutes) of six-hour arithmetic margin. This is a narrow design margin: actual camera/CPU/card current, early-cutoff capacity, converter efficiency and temperature remain critical first-article measurements. The earlier 6.388 h result omitted external path loss and is superseded. The 20% allowance is not a demonstrated discharge-curve equivalence or a lifetime guarantee.

## Factory acceptance

1. Fit the exact card, camera and battery; stream the production data format and VGA video while writing all raw channels to microSD.
2. Verify the external battery path is at most 190 mΩ equivalent at its operating temperature. Perform loop-resistance, continuity and isolation checks only on an unpowered dummy harness or disconnected board-side harness; with the protected pack connected, use a voltmeter and a current-limited controlled load/charge simulation for voltage-drop and transient measurements. Retain load-step traces and capture error counters.
3. Run from a full charge through the 3.2 V capture stop. Require at least six hours of continuous valid recordings; record the actual temperature, frame rate and packet/card loss.
4. Confirm shutdown flushes the files and leaves the pack protected, then verify USB recovery and charging temperature cutoffs.

The exact executable arithmetic and inputs are in [energy-budget.py](energy-budget.py) and [energy-budget.json](energy-budget.json). Procurement evidence is in [battery-candidate-jauch250480.json](../procurement/battery-candidate-jauch250480.json); Bulgaria delivery is still awaiting an actual supplier/checkout result.

Battery-entry topology, connector/fuse coordination and loss allocations are executable in [battery_path_checks.py](../power/battery_path_checks.py); [results](../power/battery-path-check-results.json) distinguish calculated checks from hardware acceptance.
