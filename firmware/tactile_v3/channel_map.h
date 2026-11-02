#pragma once

// Logical IDs are stable across firmware and host tooling. Each position has
// one static pressure channel and one dynamic PVDF channel.
namespace TactileV3 {
static const char *const CHANNEL_IDS[40] = {
  "I1_P","I2_P","I3_P","M1_P","M2_P","M3_P","R1_P","R2_P","R3_P","L1_P",
  "L2_P","L3_P","T1_P","T2_P","P1_P","P2_P","P3_P","P4_P","H1_P","H2_P",
  "I1_V","I2_V","I3_V","M1_V","M2_V","M3_V","R1_V","R2_V","R3_V","L1_V",
  "L2_V","L3_V","T1_V","T2_V","P1_V","P2_V","P3_V","P4_V","H1_V","H2_V"
};

// Four CD74HC4067 outputs feed a CD74HC4052 final selector:
// selector 0/1 = pressure muxes A/B, selector 2/3 = PVDF muxes A/B.
static const uint8_t MUX_OUTPUTS[4] = {0, 1, 2, 3};
static const uint8_t USED_MUX_SLOTS = 10;
}
