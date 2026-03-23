You are helping a fabrication tooling team convert a Three.js assembly at `/root/data/fabrication_scene.js` into fabrication-ready exports.

Treat each named group as a fabrication part. Each mesh belongs to its nearest named-group ancestor. Bake world transforms before export, then convert the geometry from Three.js Y-up coordinates into fabrication Z-up coordinates.

Create:

- `/root/output/fabrication_manifest.json`
- `/root/output/fabrication_links/<part_name>.obj`

Rules:

- Export exactly one merged OBJ per part using only the meshes owned directly by that part.
- Do not include meshes owned by child named groups in a parent part export.
- Use the nearest named-group ancestor as the `parent_part` relationship.
- Skip named groups that own no meshes.
- Sort parts alphabetically by `part_name`.
- `fabrication_manifest.json` must contain a top-level `parts` array. Each entry must include:
  - `part_name`
  - `parent_part` using `null` when absent
  - `mesh_count`
  - `source_meshes` sorted alphabetically
  - `link_obj`
