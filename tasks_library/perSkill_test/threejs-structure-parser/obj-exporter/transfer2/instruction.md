You are preparing a geometry audit for a bundled Three.js loader scene.

Input file in `/root/data/`:
1. `transfer2_scene.mjs`

Produce these outputs:
1. Individual mesh OBJ files in `/root/output/audit_meshes/<component_name>/<mesh_name>.obj`
2. A CSV audit ledger at `/root/transfer2_mesh_metrics.csv`

Requirements:
1. Treat each named `THREE.Group` that owns meshes as a component.
2. Assign each mesh to the nearest named parent group in its ancestor chain.
3. Export every mesh in world coordinates.
4. The CSV must contain a header row with these columns:
   - `component`
   - `mesh_file`
   - `vertex_count`
   - `face_count`
   - `min_x`
   - `min_y`
   - `min_z`
   - `max_x`
   - `max_y`
   - `max_z`
5. Add one CSV row for every exported OBJ file, sorted by component name and then mesh file name.
6. Compute the metrics from the exported geometry.
7. Do not include merged component OBJ files for this task.
