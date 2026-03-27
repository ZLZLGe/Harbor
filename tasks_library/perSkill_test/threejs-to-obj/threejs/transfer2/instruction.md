You are given a Three.js module at `/root/data/transfer2_scene.js`.
It defines a compact pallet sorter with named subassemblies and nested articulation links.

Produce these outputs:
1. `/root/output/pallet_sorter.urdf`
2. `/root/output/meshes/<link_name>.obj` for every non-empty named link

Rules:
1. Treat every named `THREE.Group` below the root container as a link candidate.
2. Each mesh belongs to its nearest named ancestor group.
3. When exporting a link OBJ, do not include geometry owned by child named links.
4. Bake world transforms into the exported geometry.
5. Skip named groups that own no geometry.
6. Use `/root/data/joint_types.json` to choose the joint type for each child link. If a link name is not present in that file, use `fixed`.
7. Write a minimal URDF:
   - one `<link>` per exported link
   - one `<joint>` for each child link whose nearest named ancestor is another named link
   - each `<mesh>` filename must use the relative path `meshes/<link_name>.obj`
8. Sort link names and joint names alphabetically for deterministic output.

The URDF root robot name must be `pallet_sorter`.
