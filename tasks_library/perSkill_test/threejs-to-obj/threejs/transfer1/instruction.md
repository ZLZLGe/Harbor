You are given a Three.js module at `/root/data/transfer1_scene.js`.
It defines an archive trolley as a scene graph with named parts, nested groups, regular meshes, and instanced components.

Write `/root/output/ownership_report.json` with this exact schema:

```json
{
  "scene_name": "archive_trolley",
  "parts": [
    {
      "name": "base_cart",
      "parent": null,
      "child_parts": ["drawer_bank"],
      "mesh_count": 1,
      "instanced_instance_count": 4,
      "owned_triangle_count": 120
    }
  ]
}
```

Rules:
1. Treat every named `THREE.Group` below the root container as a part candidate.
2. Each `Mesh` or `InstancedMesh` belongs to its nearest named ancestor group.
3. Skip named groups that own no geometry after applying the nearest-ancestor rule.
4. Sort `parts` by `name` ascending.
5. `parent` must be the nearest named ancestor part below the root container, or `null` if the part is attached directly to the root.
6. `child_parts` must list the immediate named child parts that are included in the report, sorted ascending.
7. `mesh_count` counts owned non-instanced `Mesh` nodes only.
8. `instanced_instance_count` is the total number of instances across owned `InstancedMesh` nodes.
9. `owned_triangle_count` is the total triangle count contributed by the part's owned geometry:
   - for `Mesh`, count the geometry triangles once
   - for `InstancedMesh`, multiply the geometry triangle count by the instance count

Notes:
- A named ancestor may appear in `parent` even if that ancestor is skipped from `parts` because it owns no geometry.
- Write numeric values as JSON numbers, not strings.
