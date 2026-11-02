# Tactile-core fabrication status

V3.3 contains 356 components and 244 nets. Independent native export reconciles 1,125 connected pins plus 19 intentional NC pins. The routed 90 × 60 mm four-layer core passes KiCad with zero DRC violations, unconnected pads and footprint errors.

Fabrication requires epoxy-filled, planarized, copper-capped 0.30 mm vias (IPC-4761 Type VII / VIPPO). There are 34 via locations overlapping SMD mask apertures; the manufacturing package includes their coordinates. The assembler quote must explicitly include this process.

This release is the tactile core. Continuous camera operation and the minimum six-hour system runtime, with twelve hours as a stretch target, need the separate camera and power architecture under review. The current 500 mAh battery and 100 mA charger module do not establish that system requirement.

Power, buffer and signal-chain simulations have explicit model limits. First-article rail sequencing, reference noise, harness response, cell temperature and actual current measurements remain commissioning gates. See ../verification/power-simulation.md and the current signal-chain and firmware reports. The manufacturing quote remains subject to the current approval gate; purchasing and physical assembly are separate actions.
