You are preparing an industrial safety barrier layout for a Blender-based staging mockup.

The source scene module is located at `/root/data/object.js`. It defines a barrier assembly with repeated posts, support feet, and warning hardware arranged through nested transforms.

Write a JavaScript program that exports the full assembly to Wavefront OBJ format at `/root/output/safety_barrier.obj`.

Requirements:
- Preserve the final world-space position of every mesh.
- Include repeated geometry instances in the exported result.
- Convert the model into Blender Z-up space by applying a -90 degree rotation around the X axis before export.
