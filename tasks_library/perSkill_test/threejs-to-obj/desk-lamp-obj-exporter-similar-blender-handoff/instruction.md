You are a 3D tooling engineer. The file `/root/data/lamp.js` exports a procedural Three.js desk lamp assembly through `createLampAssembly()`.

Write a Node.js script that loads that module, bakes every mesh into world space, expands the repeated screw instances into regular geometry, applies a `-90` degree rotation around the X axis so the result is in Blender Z-up coordinates, and saves one OBJ file to `/root/output/lamp.obj`.

Requirements:
- Preserve the assembled lamp layout after all nested parent transforms are applied.
- Include the repeated screws from both the base and the lamp head in the exported geometry.
- The output must be a valid OBJ with vertices and faces.
- Save only the final OBJ to `/root/output/lamp.obj`.
