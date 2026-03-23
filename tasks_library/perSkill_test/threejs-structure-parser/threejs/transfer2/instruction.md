You are helping a warehouse simulation team inspect a Three.js scene at `/root/data/rack_scene.js`.

Treat each named group as a part. Export every `THREE.InstancedMesh` instance as its own OBJ with world transforms baked.

Create:

- `/root/output/instance_report.json`
- `/root/output/instances/<part_name>/<object_name>__<two_digit_index>.obj`

Rules:

- Each instanced mesh instance belongs to the nearest named-group ancestor of the `THREE.InstancedMesh`.
- Ignore named groups that contain no instanced exports.
- Sort parts by `part_name`.
- Within each part, sort exported filenames alphabetically.
- `instance_report.json` must contain a top-level `parts` array. Each part entry must include:
  - `part_name`
  - `parent_part` using `null` when absent
  - `exported_files`
  - `export_count`
