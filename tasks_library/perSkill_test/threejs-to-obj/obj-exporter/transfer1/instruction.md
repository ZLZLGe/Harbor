You are helping an automation team extract a single assembly from a larger Three.js layout.

The scene file is located at `/root/data/inspection_line.js` and exposes `createScene()`.

Write a JavaScript solution that exports only the object named `inspection_fixture` and its mesh descendants to `/root/output/inspection_fixture.obj`. Keep the exported geometry in the same world-space placement it has inside the full scene, including nested transforms and instanced meshes.

The OBJ must be suitable for Blender import, so convert the exported geometry to Blender Z-up space with a `-90` degree rotation around the X axis before writing the file.
