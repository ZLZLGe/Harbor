You are helping an operations team inspect a Three.js ride model stored at `/root/data/ride_scene.js`.

Parse the scene and determine the part-level structure using named groups as parts. Each mesh belongs to its nearest named group ancestor. Bake world transforms before export.

Write the results to `/root/output` with this structure:

`/root/output/part_meshes/<part_name>/<mesh_name>.obj`
`/root/output/links/<part_name>.obj`
`/root/output/part_inventory.json`

`part_inventory.json` must be a JSON object with a top-level `parts` array. Each element must contain:

- `part_name`
- `parent_part` using `null` when the part has no named-group parent
- `mesh_names` sorted alphabetically
- `part_mesh_dir`
- `link_obj`

Sort the `parts` array by `part_name`. Skip named groups that own no meshes.
