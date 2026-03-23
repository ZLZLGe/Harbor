You are preparing a leaf-part mesh pack from a Three.js service cart assembly.

The source scene module is `/root/data/service_cart.js` and exports `createScene()`.

Treat every named `THREE.Group` as a part. Each mesh belongs to its nearest named ancestor group. Build the named-group parent tree using nearest named ancestor groups.

Write a JavaScript script that:
1. Finds every non-empty leaf part in that named-group tree.
2. Exports one OBJ per leaf part to `/root/output/leaves/<part_name>.obj`.
3. Bakes mesh world transforms before export.
4. Converts the exported geometry to Blender Z-up space by applying a `-90` degree rotation around the X axis before writing each OBJ.
5. Writes `/root/output/leaf_parts_index.json`.

The index must be a JSON object with:
- `leaf_part_count`
- `total_leaf_meshes`
- `leaf_parts`

`leaf_parts` must be sorted by `part_name`. Each entry must contain:
- `part_name`
- `ancestor_chain`
- `obj_path`
