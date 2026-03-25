You are packaging a modular showroom concept into a single exchange mesh.

The component factory file is located at `/root/data/component_factory.js`, and the placement plan is stored in `/root/data/assembly_plan.json`.

Write a JavaScript solution that reads the placement plan, instantiates the listed component factories, applies the planned transforms, assembles the complete display, and exports the final combined geometry to `/root/output/modular_display.obj`.

Preserve the assembled model in its intended world-space placement, including nested transforms and instanced meshes inside any component. The OBJ must be ready for Blender import, so apply a `-90` degree rotation around the X axis before writing the file.
