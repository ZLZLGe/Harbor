You are preparing a cabinet assembly from a Three.js scene for downstream part handling.

The source scene module is `/root/data/cabinet_scene.js` and exports `createScene()`.

Treat every named `THREE.Group` as a part. Each mesh belongs to its nearest named ancestor group.

Write a JavaScript script that:
1. Exports one OBJ file per non-empty part to `/root/output/parts/<part_name>.obj`.
2. Bakes mesh world transforms before export.
3. Converts the exported geometry to Blender Z-up space by applying a `-90` degree rotation around the X axis before writing each OBJ.
4. Writes `/root/output/part_manifest.json`.

The manifest must be a JSON object with a top-level `parts` array sorted by `part_name`. Each part entry must contain:
- `part_name`
- `mesh_names`
- `obj_path`

`mesh_names` must be sorted.
