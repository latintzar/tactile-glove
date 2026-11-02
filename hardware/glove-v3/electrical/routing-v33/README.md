# V3.3 routing record

These scripts record the bounded correction run in `/tmp/glove-eda-runtime/power-cad-fix`. They preserve the existing board, fit the reference/buffer/protection corrections, route actual KiCad opens, repair three trapped terminals, remove orphan stubs and independently reconcile all physical pins. Their runtime paths are historical execution paths; the authoritative editable deliverable is `../glove-v3-routed.kicad_pcb`, with canonical topology in `../components.json`.

The final full KiCad check reports zero violations, zero open connections and zero footprint errors. Design rules were preserved. Body markings were moved from silkscreen to fabrication layers in the board and local library; land patterns and courtyards remain unchanged.

An additional assembly audit found 34 via locations whose drills overlap SMD mask apertures. This release requires IPC-4761 Type VII epoxy-filled and copper-capped vias, as specified in the manufacturing package.
