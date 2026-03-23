You are preparing a visitor information kiosk model for downstream editing in Blender.

The source scene module is located at `/root/data/object.js`. It defines a finished kiosk assembly with nested transforms, mirrored details, and repeated mounting hardware.

Write a JavaScript program that exports the full assembly to Wavefront OBJ format at `/root/output/info_kiosk.obj`.

Requirements:
- Preserve the final world-space position of every mesh.
- Include repeated geometry instances in the exported result.
- Convert the model into Blender Z-up space by applying a -90 degree rotation around the X axis before export.
