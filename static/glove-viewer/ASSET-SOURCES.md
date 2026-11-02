# Hand-view assets

The reference anatomy is a generic, skinned right-hand mesh. It illustrates anatomy and candidate sensing roles. Its proportions are independent of wearer measurements, a glove pattern, and validated sensor placement.

## Hand mesh

- Package: `@webxr-input-profiles/assets@1.0.20`
- Asset: `dist/profiles/generic-hand/right.glb`
- Source: https://cdn.jsdelivr.net/npm/@webxr-input-profiles/assets@1.0.20/dist/profiles/generic-hand/right.glb
- Upstream: https://github.com/immersive-web/webxr-input-profiles/tree/main/packages/assets/profiles/generic-hand
- License: MIT; Copyright (c) 2019 Amazon. Full retained notice: `hand-LICENSE.txt`.
- Package license source: https://cdn.jsdelivr.net/npm/@webxr-input-profiles/assets@1.0.20/LICENSE.md
- SHA-256: `291790c14f7f88a7f9bd35330c47392ed8e8d395ae6728f4bb7089f1bc1f2b96`
- Size: 94,004 bytes. glTF 2.0, one skinned mesh, 1,360 vertices, 2,314 triangles, 25 named joints, one material, no external textures, no baked animations.
- glTF linear units are metres. The source mesh extends 77.022 × 212.041 × 145.906 mm in its original X/Y/Z axes; these are asset bounds, not glove dimensions.
- Every joint is a sibling under `Armature`. The viewer retains the authored bind pose. It does not assume a parent-child finger rig or animate unverified joint motion.
- The display applies a proper rotation: display X=source Z, display Y=−source Y, display Z=source X, and puts the wrist at the origin. The dorsal surface faces display +Z; fingers point approximately +Y.

## Renderer

Three.js `0.180.0` (revision 180), MIT; Copyright © 2010–2025 three.js authors. Full retained notice: `three-LICENSE.txt`.

The files come from the corresponding pinned npm package at https://cdn.jsdelivr.net/npm/three@0.180.0/ :

- `build/three.module.min.js` → `three.module.js`
- `build/three.core.min.js` → `three.core.js`
- `examples/jsm/loaders/GLTFLoader.js`
- `examples/jsm/controls/OrbitControls.js`
- `examples/jsm/utils/BufferGeometryUtils.js`

Only import specifiers are rewritten to local relative paths. The private page loads these files from the same origin; runtime CDN requests and import maps are unnecessary.
