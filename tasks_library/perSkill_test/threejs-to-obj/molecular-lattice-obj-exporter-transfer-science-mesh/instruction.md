You are preparing a crystal-structure handoff for a scientific visualization pipeline. The file `/root/data/lattice.js` exports `createMolecularLatticeScene()`, which builds a molecular lattice from nested groups, atom spheres, and bond cylinders. The atoms are repeated across a crystal supercell through instancing.

Write a Node.js script that loads that module, bakes every mesh into world space, expands the instanced atoms into regular geometry, applies a `-90` degree rotation around the X axis so the result is in Blender Z-up coordinates, and saves one OBJ file to `/root/output/lattice.obj`.

Requirements:
- Preserve the molecular lattice layout after all parent transforms are applied.
- Include every repeated atom site and every bond cylinder in the exported geometry.
- The output must be a valid OBJ with vertices and faces.
- Save only the final OBJ to `/root/output/lattice.obj`.
