You are preparing a filtered yard model for a downstream CAD handoff.

The Three.js scene file is located at `/root/data/loading_yard.js` and exports `createScene()`.

Write a JavaScript solution that exports only the meshes that belong to nodes marked with `userData.exportable === true` to `/root/output/loading_yard.obj`. Preserve the selected geometry in its original world-space placement, including nested transforms and instanced meshes, and ignore all other helper or reference geometry in the scene.

The exported OBJ must be ready for Blender import, so apply a `-90` degree rotation around the X axis before writing the file.
