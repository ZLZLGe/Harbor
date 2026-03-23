You are helping a robotics tooling team convert a Three.js assembly at `/root/data/robot_scene.js` into a URDF package.

Treat each named group as a link. Each mesh belongs to its nearest named-group ancestor. Bake world transforms before export.

Create:

- `/root/output/robot_arm.urdf`
- `/root/output/meshes/<link_name>.obj`

Rules:

- Export exactly one merged OBJ per link using only the meshes owned directly by that link.
- Use the nearest named-group ancestor as the parent link relationship.
- Use `fixed` joints only.
- Name each joint `<parent_link>__to__<child_link>`.
- In the URDF, sort links alphabetically and sort joints alphabetically by joint name.
- Reference mesh files as `meshes/<link_name>.obj`.
