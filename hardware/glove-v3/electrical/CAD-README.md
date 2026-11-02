# Native electrical sources

`components.json` is the canonical circuit graph. `glove-v3.kicad_sch` and its11 native sheets contain connected physical pin boxes for329 parts. The symbols use passive electrical pin types, so their ERC result is not a functional pin-type audit. Exact package/pin evidence is tracked separately.

`native-net-reconciliation.json` compares the exported KiCad XML with the canonical graph:238 connected nets,1051 connected pins. `glove-v3-schematic.pdf` is the exported review document. `glove-v3-floorplan.kicad_pcb` is a70×46mm four-layer placement candidate with exact footprints and329 placedcomponents. It is unrouted and not released for fabrication. The initial autorouter trial failed to finish and produced no verified route.

`glove-v3.sch`, `cells_*.sch`, `support.sch`, `glove-v3.net`, and `schematic.svg` are obsolete intermediate captures. Use the native source above; these older files are retained only as development history. `generate_native.py`, `set_footprints.py`, and `build_board.py` reproduce the current native sources/placement; analog placement and routing are still engineering work.
