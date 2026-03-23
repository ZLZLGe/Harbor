You are auditing a Three.js line fixture assembly.

The source scene module is `/root/data/line_fixture.js` and exports `createScene()`.

Treat every named `THREE.Group` as a part. Each mesh belongs to its nearest named ancestor group. The parent part for a named group is its nearest named ancestor group.

Write a JavaScript script that produces `/root/output/link_audit.json`.

The output must be a JSON object with a top-level `parts` array sorted by `part_name`. Each part entry must contain:
- `part_name`
- `parent_part`
- `child_parts`
- `owned_meshes`
- `mesh_count`
- `triangle_count`
- `world_bbox_min`
- `world_bbox_max`

Rules:
1. `child_parts` must list only direct child parts in the named-group hierarchy, sorted.
2. `owned_meshes` must be sorted.
3. `world_bbox_min` and `world_bbox_max` must be 3-element arrays of numbers computed from the owned meshes after baking world transforms.
4. Skip named groups that own no meshes.
