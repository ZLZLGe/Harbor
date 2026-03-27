You are given a Three.js module at `/root/data/transfer3_scene.js`.
It defines a packaging-line fixture as a scene graph with named parts, nested groups, mirrored scaling, and instanced components.

Write `/root/output/geometry_audit.csv` with this exact header:

```text
name,parent,piece_count,vertex_count,face_count,min_x,min_y,min_z,max_x,max_y,max_z
```

Rules:
1. Treat every named `THREE.Group` below the root container as a part candidate.
2. Each mesh belongs to its nearest named ancestor group.
3. When summarizing a part, do not include geometry owned by child named parts.
4. Expand every `THREE.InstancedMesh` into separate geometry pieces.
5. Bake world transforms into geometry before measuring it.
6. Convert geometry from Three.js Y-up into Blender Z-up with a `-90` degree rotation around the X axis before computing metrics.
7. Skip named groups that own no geometry after applying the nearest-ancestor rule.
8. Sort rows by `name` ascending.
9. `parent` must be the nearest named ancestor part below the root container, or an empty string when the part is attached directly to the root.
10. `piece_count` is the number of baked geometry pieces after expanding instances.
11. `vertex_count` is the total number of position rows across all baked pieces after converting indexed geometry to non-indexed.
12. `face_count` is the total triangle count after baking.
13. Format every bounding-box number with exactly six digits after the decimal point.
