You are packaging a Three.js inspection rig into a minimal URDF asset pack.

The scene module is `/root/data/inspection_rig.js` and exports `createScene()`.

Treat every named `THREE.Group` as a link. The parent link for a named group is its nearest named ancestor group. Each mesh belongs to its nearest named ancestor group.

Write a JavaScript script that:
1. Exports one OBJ per non-empty link to `/root/output/meshes/<link_name>.obj`.
2. Bakes mesh world transforms before export.
3. Converts the exported geometry to Blender Z-up space by applying a `-90` degree rotation around the X axis before writing each OBJ.
4. Writes `/root/output/inspection_rig.urdf`.

URDF requirements:
1. The robot name must be `inspection_rig`.
2. Emit one `<link>` element per non-empty named group.
3. Emit one fixed joint for each link that has a parent link.
4. Sort links and joints by name for deterministic output.
5. Reference mesh filenames as `meshes/<link_name>.obj`.
