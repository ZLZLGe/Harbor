The file `/root/data/object.js` defines a desk lamp scene with a single `createScene()` function. The lamp is organized into named segment groups, and each segment may contain meshes inside unnamed helper groups used only for transforms.

Parse the scene and export geometry into `/root/output` with this layout:

```text
/root/output/
├── part_meshes/
│   ├── lamp_base/
│   │   ├── weighted_base.obj
│   │   ├── stem_column.obj
│   │   └── ...
│   ├── lower_arm/
│   ├── upper_arm/
│   └── lamp_head/
└── links/
    ├── lamp_base.obj
    ├── lower_arm.obj
    ├── upper_arm.obj
    └── lamp_head.obj
```

Requirements:

1. Use the nearest named `THREE.Group` ancestor as the owning segment for each mesh.
2. Export every mesh in world coordinates to `/root/output/part_meshes/<segment>/<mesh_name>.obj`.
3. For each segment, also export a merged OBJ containing all meshes assigned to that segment at `/root/output/links/<segment>.obj`.
4. Keep the original mesh names for filenames. If a mesh is unnamed, assign `unnamed_mesh_<n>`.
5. The final scene should produce outputs for these segment names: `lamp_base`, `lower_arm`, `upper_arm`, and `lamp_head`.
