You are a helpful 3D programmer working on a museum display export pipeline.

The Three.js scene file is located at `/root/data/pedestal_showpiece.js` and exports a complete assembled display object through `createScene()`.

Write a JavaScript solution that exports the full assembled object to OBJ format at `/root/output/pedestal_showpiece.obj`. The exported geometry must preserve the scene's world-space placement, including nested transforms and instanced meshes.

The OBJ must be ready for Blender import, so convert the output to Blender Z-up space by applying a `-90` degree rotation around the X axis before writing the file.
