# FreeRouting review — 2026-10-23

This is a bounded scratch review of an unapplied routing proposal. The canonical source board remains `hardware/glove-v4/electrical/glove-v4-routing-candidate.kicad_pcb`, SHA256 `973111f03d52a0288c53378c9ba5df2dc6b7ac896ce2e6f88557ab0d7846a84b`.

FreeRouting job `652C15\\59F0E5` ran from 05:57:59Z to 06:02:09Z on a conservative planner DSN. It began at 384 unrouted items and finished pass 1 at 296 unrouted items, with 1,644 pre-existing fixed trace/via violations. The emitted SES had SHA256 `ff1456a201af262a194f54354dd1a437af13f82f45973d6d29828fef1f626045` and contained 318 additional copper segments relative to the source count.

A scratch SES import produced a review candidate with 13 native unconnected items versus 20 in the source DRC. Seven connection instances closed across seven unique nets: `IO1_SPARE4`, `MUX_SHIFT_CLK`, `SD_CD_N`, one of two `USB_CC1` opens, `USB_CFG_ATTACH_N`, `USB_CONFIG_CLR_N`, and `USB_NOT_SUSPEND`. Native DRC reported zero other error classes in that candidate; dangling track/via warnings remained.

The SES-import board and planner artifacts were unavailable when the follow-up audit was attempted. The candidate therefore cannot be promoted, and this note does not claim physical validation, release readiness, or canonical board changes. A reproducible candidate and its native checks must be restored before any independent promotion decision.
