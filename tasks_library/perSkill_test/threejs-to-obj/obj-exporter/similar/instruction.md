You are preparing a staged studio display model for downstream editing in Blender.

The source scene module is located at `/root/data/object.js`. It exports `createScene()` and defines a completed display assembly with nested transforms, mirrored placard geometry, and repeated fasteners.

Write a JavaScript program that exports the full assembly to Wavefront OBJ format at `/root/output/studio_display.obj`.

Requirements:
- Preserve the final world-space position of every mesh.
- Include repeated geometry instances in the exported result.
- Convert the model into Blender Z-up space by applying a -90 degree rotation around the X axis before export.
