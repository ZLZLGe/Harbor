You are preparing bundled OBJ deliverables for a bundled Three.js bridge-response kit scene.

Input files in `/root/data/`:
1. `transfer3_scene.mjs`
2. `transfer3_bundle_rules.json`

Produce these outputs:
1. One merged OBJ file for each bundle in `/root/output/bundles/<bundle_name>.obj`
2. A bundle report JSON file at `/root/transfer3_bundle_report.json`

Requirements:
1. Treat each named `THREE.Group` as a component.
2. Use `transfer3_bundle_rules.json` to decide which components belong to each bundle.
3. For each bundle, merge all meshes owned by all listed components into a single OBJ file in world coordinates.
4. Keep the bundle order exactly as listed in the rules file.
5. The report JSON must contain these top-level keys:
   - `scene`
   - `bundles`
   - `tool_called`
6. `bundles` must be an array in rule order. Each entry must contain:
   - `bundle`
   - `components`
   - `target_obj`
   - `mesh_count`
   - `vertex_count`
7. Set `tool_called` to `["bundle_obj_export"]`.
