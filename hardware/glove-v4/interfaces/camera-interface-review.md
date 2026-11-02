# V4 camera interface independent review

Reviewed: 2026-10-22

Scope: `hardware/glove-v4/interfaces/camera-interface.json` and its generator. The generated JSON contains 37 components. The generator was not modified.

## Confirmed maps

- The CamThink OV5640 page matches connector pins 1–24 in the generated map, including SDA/SCL, AVDD, RESET, VSYNC, PWDN, HREF, DVDD, DOVDD, XCLK, PCLK, and NC pins. Its DVP data names are D9, D8, D7, D6, D2, D5, D3, D4; the generated `CAM_D0..CAM_D7` names intentionally map those eight wires in order D2..D9 for the MCU byte lanes.
- TI's commercial SN74AXC8T245 pin map matches the generated TSSOP-24 wiring: VCCA pin 1, DIR1 pin 2, A pins 3–10, DIR2 pin 11, grounds 12/13, B pins 14–21, OE pin 22, VCCB pins 23/24. DIR1 high/DIR2 low gives A-to-B for all data bits; DIR1 high/DIR2 high gives A-to-B for bits 1–4 and B-to-A for bits 5–8. This matches the data and mixed-direction control use. [TI datasheet](https://www.ti.com/lit/ds/symlink/sn74axc8t245.pdf)
- Nexperia's 2N7002 pinout is gate/source/drain = 1/2/3, matching both open-drain clamps. Nexperia's 74LVC1G04GW pinout is NC/input/GND/output/VCC = 1/2/3/4/5, also matching the inverter map.
- TI's PCA9306 pinout is GND/VREF1/SCL1/SDA1/SDA2/SCL2/VREF2/EN = 1..8. The generated map is correct and ties VREF2 and EN, with a 200 kΩ pullup and MOSFET isolation. The 1.8 V to 3.3 V reference relationship is valid.
- TI's TPS7A20 DBV pinout is IN/GND/EN/NC/OUT = 1/2/3/4/5, matching all three LDOs. The device provides output discharge when EN is low and requires effective output capacitance; the generated 10 µF + 100 nF network and 100 kΩ enable pulldowns are consistent with that requirement.

## Findings requiring resolution

1. **Exact module variant electrical confirmation is still required.** The generic OmniVision specification permits 1.8 V or 2.8 V I/O, so the 1.8 V translator path is chip-compatible. CamThink's current shipped electrical note explicitly calls out DOVDD = 2.8 V for its current 60°/15 cm module/NE101 configuration, while the page does not publish a separate electrical table for the selected 120°/8 cm variant. This is a supplier-variant evidence gap, not evidence that the generated 1.8 V circuit is electrically impossible. Obtain the exact supplied module part number and electrical table before release.

2. **External DVDD is supported, with a documented power tradeoff.** OmniVision recommends internal DVDD for 1.8 V I/O to minimize power-down current, while its section 2.7.2 explicitly defines an external-DVDD power-up sequence. The generated sequence is DOVDD → AVDD → DVDD, then PWDN low, XCLK, RESET release, and more than 20 ms before SCCB probe, which follows that external-DVDD sequence. The design record should retain the all-rails-off shutdown behavior and document why external DVDD is selected.

3. **The connector source URL in the generator is wrong.** The exact Hirose `FH12-24S-0.5SH(55)` is official part `CL0586-0521-0-55`, not `CL0586-0560-7-55`. Correct source: https://www.hirose.com/product/p/CL0586-0521-0-55. Hirose confirms bottom contact, 24 positions, 0.5 mm pitch, horizontal ZIF, 0.3 mm FPC, and 2.0 mm height. The module page confirms 24-pin/0.5 mm pitch but does not provide the supplied flex tail contact side, stiffener, or insertion depth; cable mating remains an assembly gate.

The OmniVision source used by the generator is valid: https://files.waveshare.com/upload/d/da/OV5640_DataSheet.pdf. The module pin and variant source is https://wiki.camthink.ai/docs/hardware-dev-resources/camera-module-ov5640/. The TI and Nexperia URLs in the generator resolve to the relevant device datasheets.

## Closure recommendation

Retain the generated SN74AXC8T245 topology and the documented 1.8 V camera-I/O path for this revision. The commercial SN74AVC8T245PWR is not a drop-in replacement: its 24-pin control/power assignment differs from the AXC mixed-direction wiring, including pin 11, so the earlier AVC substitution proposal is withdrawn.

CamThink's generic OV5640 module documentation permits DOVDD from 1.8 V to 2.8 V. The current published 2.8 V production note describes a different module configuration, and 2.8 V is the selected module's upper documented limit; rail tolerance must not cross that limit without an exact module electrical table. The 1.8 V AXC path is therefore the evidence-backed design choice pending confirmation of the supplied 120-degree module. External DVDD = 1.5 V remains supported by the OV5640 external-DVDD power-up sequence.

Power-off sequencing remains: hold CAM_IF_EN/OE low, remove camera rails, and retain host-side pullups and isolation. PCA9306 remains within its published reference ranges for the host-side SCCB rail. The Hirose connector remains the mechanical gate: verify the supplied flex tail's contact side, stiffener, exposed length, and insertion depth against `CL0586-0521-0-55` before first article.
