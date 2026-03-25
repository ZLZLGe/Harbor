You are preparing crate-ready OBJ assets for a bundled Three.js greenhouse equipment scene.

Input files in `/root/data/`:
1. `transfer1_scene.mjs`
2. `transfer1_export_plan.json`

Produce these outputs:
1. One merged OBJ file per requested crate in `/root/output/crates/<crate_label>.obj`
2. A packing summary JSON file at `/root/transfer1_crate_summary.json`

Requirements:
1. Treat each named `THREE.Group` as a candidate component.
2. Only export the components listed in `transfer1_export_plan.json`.
3. For each request, merge all meshes owned by the named component into a single OBJ file in world coordinates.
4. Name each OBJ file using the `crate_label` from the plan, not the original component name.
5. The summary JSON must contain these top-level keys:
   - `scene`
   - `requests`
   - `crates`
   - `tool_called`
6. `requests` must echo the requested component names in the same order as the plan.
7. `crates` must be an array in request order. Each entry must contain:
   - `crate_label`
   - `source_component`
   - `target_obj`
   - `mesh_count`
   - `vertex_count`
8. Set `tool_called` to `["crate_component_export"]`.
