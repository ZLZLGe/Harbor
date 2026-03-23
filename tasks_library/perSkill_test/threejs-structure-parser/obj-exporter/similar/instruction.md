You are preparing an OBJ handoff for a bundled Three.js inspection tower scene.

Input file in `/root/data/`:
1. `similar_scene.mjs`

Produce these outputs:
1. Individual mesh OBJ files in `/root/output/component_meshes/<component_name>/<mesh_name>.obj`
2. One merged component OBJ file for each component in `/root/output/component_links/<component_name>.obj`
3. A manifest JSON file at `/root/similar_component_manifest.json`

Requirements:
1. Treat each named `THREE.Group` that owns at least one mesh as a component.
2. Assign each mesh to the nearest named parent group in its ancestor chain.
3. Export every mesh in world coordinates.
4. The merged component OBJ must contain all meshes assigned to that component, also in world coordinates.
5. The manifest JSON must contain these top-level keys:
   - `scene`
   - `components`
   - `totals`
   - `tool_called`
6. `components` must be an array sorted by component name. Each entry must contain:
   - `component`
   - `mesh_dir`
   - `merged_obj`
   - `mesh_files`
   - `mesh_count`
7. `totals` must contain:
   - `component_count`
   - `mesh_count`
8. Set `tool_called` to `["component_obj_export"]`.
