# Contributing

Start with the [product tour](docs/product-tour.md), [module map](docs/module-map.md) and [current status](docs/status.md). Keep the concept, source checks and physical measurements explicit when changing the design or its explanation.

## Check a change

Run the relevant [host checks](docs/setup.md#host-checks). After intentional edits, review and stage the files you want to publish, then refresh the public inventory:

```sh
git add <files-you-reviewed>
python3 tools/refresh_inventory.py
python3 tools/check_package.py
git add provenance/public-files.json
```

The refresh reads only Git-tracked/staged paths. Unchanged files keep their source classes. Edited or new files become `post-release-change`; an edited file retains its previous public hash/class and any original source hash. Removed files keep an explicit history record. The original `f40271c6331db255bce6df60d84f0953fbe18355` source snapshot stays fixed.

The inventory describes file bytes. Native board/manufacturing manifests, routing/DRC results, geometry/clearance records, firmware compile evidence and physical acceptance each need their own appropriate regeneration after a relevant change. Preserve dated evidence and describe the new result separately. Review [licences and credits](THIRD-PARTY-NOTICES.md) when adding or adapting external material.
