import * as THREE from "three";

export function createBaseModule() {
  const group = new THREE.Group();
  group.name = "base_module";

  const deck = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.42, 2.1));
  deck.position.set(0, 0.21, 0);
  group.add(deck);

  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 1.85, 24));
  mast.position.set(-1.0, 1.14, -0.45);
  group.add(mast);

  const brace = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.18, 0.18));
  brace.position.set(-0.45, 1.82, -0.45);
  brace.rotation.z = -Math.PI / 7;
  group.add(brace);

  return group;
}

export function createSensorArch() {
  const group = new THREE.Group();
  group.name = "sensor_arch";

  const arch = new THREE.Mesh(new THREE.TorusGeometry(1.1, 0.1, 16, 64, Math.PI));
  arch.rotation.z = Math.PI;
  arch.rotation.x = Math.PI / 2;
  arch.position.set(0, 1.4, 0);
  group.add(arch);

  const postGeometry = new THREE.BoxGeometry(0.16, 1.5, 0.2);
  const leftPost = new THREE.Mesh(postGeometry);
  leftPost.position.set(-1.1, 0.72, 0);
  group.add(leftPost);

  const rightPost = leftPost.clone();
  rightPost.position.x = 1.1;
  group.add(rightPost);

  const emitters = new THREE.InstancedMesh(
    new THREE.BoxGeometry(0.14, 0.14, 0.3),
    new THREE.MeshBasicMaterial(),
    5,
  );
  const helper = new THREE.Object3D();
  for (let index = 0; index < 5; index += 1) {
    helper.position.set(-0.7 + index * 0.35, 1.4, 0.26);
    helper.rotation.x = Math.PI / 8;
    helper.updateMatrix();
    emitters.setMatrixAt(index, helper.matrix);
  }
  emitters.instanceMatrix.needsUpdate = true;
  group.add(emitters);

  return group;
}

export function createPanelWing() {
  const group = new THREE.Group();
  group.name = "panel_wing";

  const panel = new THREE.Mesh(new THREE.BoxGeometry(1.8, 1.1, 0.08));
  panel.position.set(0, 1.0, 0);
  group.add(panel);

  const spine = new THREE.Mesh(new THREE.BoxGeometry(0.12, 2.0, 0.22));
  spine.position.set(-0.78, 1.0, -0.05);
  group.add(spine);

  const foot = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.14, 0.5));
  foot.position.set(-0.78, 0.07, 0);
  group.add(foot);

  return group;
}
