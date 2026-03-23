You are preparing a circular light canopy model for downstream staging work in Blender.

The source scene module is located at `/root/data/object.js`. It exports `createScene()` and defines a completed canopy assembly with repeated radial arms, repeated light cells, support struts, and a nested banner mount.

Write a JavaScript program that exports the full assembly to Wavefront OBJ format at `/root/output/light_canopy.obj`.

Requirements:
- Preserve the final world-space position of every mesh.
- Include repeated geometry instances in the exported result.
- Convert the model into Blender Z-up space by applying a -90 degree rotation around the X axis before export.
