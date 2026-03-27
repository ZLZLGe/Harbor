You are given a Three.js module at `/root/data/similar_scene.js`.
It defines a desk inspection lamp as a scene graph with named parts, nested groups, transforms, and one instanced fastener cluster.

Write a Node.js solution that produces these outputs:
1. `/root/output/link_manifest.json`
2. `/root/output/links/<part_name>.obj` for every non-empty named part

Rules:
1. Treat every named `THREE.Group` below the root container as a part candidate.
2. Each mesh belongs to its nearest named ancestor group.
3. When exporting a part, do not include geometry owned by child named parts.
4. Expand any `THREE.InstancedMesh` into ordinary geometry before export.
5. Bake world transforms into geometry before writing OBJ files.
6. Convert geometry from Three.js Y-up into Blender Z-up with a `-90` degree rotation around the X axis.
7. Skip named groups that own no geometry after applying the nearest-ancestor rule.
8. Sort part names alphabetically for deterministic output.

Write `/root/output/link_manifest.json` with this exact schema:

```json
{
  "scene_name": "inspection_lamp",
  "parts": [
    {
      "name": "base_frame",
      "parent": null,
      "obj_file": "links/base_frame.obj",
      "vertex_count": 123,
      "face_count": 41
    }
  ]
}
```

Additional requirements:
- `scene_name` must be the scene root name.
- `parent` must be the nearest named ancestor part, or `null` if the part is attached directly to the root container.
- `vertex_count` and `face_count` must describe the written OBJ file.
- Write all OBJ files under `/root/output/links/`.
- Use lowercase JSON `null`, not the string `"null"`.
