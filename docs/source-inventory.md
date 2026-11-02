# Public source inventory

## Included source

This package selects reusable glove engineering from source snapshot `f40271c6331db255bce6df60d84f0953fbe18355`: current V4 hardware, firmware, protocol/host checks, enclosure and assembly source; the V3 sensing/electrical/header dependencies and meaningful earlier board/fabrication record; and a labelled earlier Bela experiment figure.

[`provenance/public-files.json`](../provenance/public-files.json) records each distributed path, size, SHA256, source class and whether its bytes match the source snapshot or are an explicitly curated public derivative. [`vendor-references.json`](../provenance/vendor-references.json) retains original publisher URLs and hashes for manufacturer/reference documents omitted from redistribution. Public curation makes source paths portable, removes private correspondence/commerce records, reconciles current status and adds licence notices; native canonical PCB/STL bytes stay preserved.

## Native fabrication sets

- Current main V4 native source: [`electrical/`](../hardware/glove-v4/electrical/); canonical board SHA256 `973111f03d52a0288c53378c9ba5df2dc6b7ac896ce2e6f88557ab0d7846a84b`.
- Separate V4 hand tile: [`interfaces/hand-tile/manufacturing/`](../hardware/glove-v4/interfaces/hand-tile/manufacturing/), including exact native exports, BOM/CPL, Gerbers, drills and maps named by its manifest.
- Earlier camera-free V3: [`glove-v3/electrical/manufacturing/`](../hardware/glove-v3/electrical/manufacturing/), with its own native export hashes and physical/fabricator acceptance requirements.
- Enclosure: [`enclosure/`](../hardware/glove-v4/enclosure/), containing generator, 48 STLs, scene/placement/part manifests and independent nominal audits.

## External references and private custody

Manufacturer datasheets, downloaded publisher HTML and vendor SPICE/model binaries retain their original publishers and terms. Their URLs/hashes and engineering reading evidence stay useful in the public source; obtain matching originals for a full regeneration that needs them. Project-generated schematic and drill-map PDFs are included with their native source and manufacturing manifests.

Supplier correspondence, shopping carts, shipping/account details, authenticated-host acceptance records, provider configuration, raw recording archives and model state remain in their original private custody. The local design server, firmware source and host tests use the public source subset. See [third-party notices](../THIRD-PARTY-NOTICES.md) for redistributed library/driver/asset terms.

## Intentional changes

Follow [Contributing](../CONTRIBUTING.md) to stage reviewed files, run `python3 tools/refresh_inventory.py`, and check the updated inventory. Edited/new files are marked as post-release changes while their original recorded provenance remains intact. Native design, fabrication and firmware evidence have their own regeneration steps.
