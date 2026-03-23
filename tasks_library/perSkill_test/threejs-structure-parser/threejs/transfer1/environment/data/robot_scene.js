import * as THREE from 'three';

function createStrut(start, end, radius, name) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();
  const geometry = new THREE.CylinderGeometry(radius, radius, length, 14);
  const mesh = new THREE.Mesh(geometry);
  mesh.name = name;
  mesh.position.copy(start).add(direction.clone().multiplyScalar(0.5));
  mesh.quaternion.setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    direction.clone().normalize(),
  );
  return mesh;
}

export function createScene() {
  const root = new THREE.Group();
  root.name = 'inspection_robot';

  const baseLink = new THREE.Group();
  baseLink.name = 'base_link';
  root.add(baseLink);

  const plinth = new THREE.Mesh(new THREE.BoxGeometry(6, 1.2, 5));
  plinth.name = 'plinth';
  plinth.position.set(0, 0.6, 0);
  baseLink.add(plinth);

  const wheelLeft = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 0.9, 24));
  wheelLeft.name = 'wheel_left';
  wheelLeft.rotation.z = Math.PI / 2;
  wheelLeft.position.set(-2.2, 0.8, 1.8);
  baseLink.add(wheelLeft);

  const wheelRight = wheelLeft.clone();
  wheelRight.name = 'wheel_right';
  wheelRight.position.z = -1.8;
  baseLink.add(wheelRight);

  const shoulderLink = new THREE.Group();
  shoulderLink.name = 'shoulder_link';
  shoulderLink.position.set(0.4, 1.2, 0);
  baseLink.add(shoulderLink);

  const shoulderColumn = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.7, 4.8, 20));
  shoulderColumn.name = 'shoulder_column';
  shoulderColumn.position.set(0, 2.4, 0);
  shoulderLink.add(shoulderColumn);

  const shoulderCollar = new THREE.Mesh(new THREE.TorusGeometry(0.85, 0.12, 10, 28));
  shoulderCollar.name = 'shoulder_collar';
  shoulderCollar.rotation.x = Math.PI / 2;
  shoulderCollar.position.set(0, 4.5, 0);
  shoulderLink.add(shoulderCollar);

  const forearmLink = new THREE.Group();
  forearmLink.name = 'forearm_link';
  forearmLink.position.set(0.1, 4.7, 0.4);
  forearmLink.rotation.z = Math.PI / 7;
  shoulderLink.add(forearmLink);

  const forearmBeam = new THREE.Mesh(new THREE.BoxGeometry(1.2, 4.5, 1.0));
  forearmBeam.name = 'forearm_beam';
  forearmBeam.position.set(0.4, 2.1, 0);
  forearmLink.add(forearmBeam);

  const forearmBrace = createStrut(
    new THREE.Vector3(-0.4, 0.6, -0.2),
    new THREE.Vector3(0.9, 4.2, 0.2),
    0.12,
    'forearm_brace',
  );
  forearmLink.add(forearmBrace);

  const toolLink = new THREE.Group();
  toolLink.name = 'tool_link';
  toolLink.position.set(0.7, 4.3, 0);
  forearmLink.add(toolLink);

  const wristBlock = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.8, 0.9));
  wristBlock.name = 'wrist_block';
  wristBlock.position.set(0, 0.3, 0);
  toolLink.add(wristBlock);

  const gripperLeft = new THREE.Mesh(new THREE.BoxGeometry(0.25, 1.2, 0.25));
  gripperLeft.name = 'gripper_left';
  gripperLeft.position.set(0.4, -0.6, 0.25);
  toolLink.add(gripperLeft);

  const gripperRight = gripperLeft.clone();
  gripperRight.name = 'gripper_right';
  gripperRight.position.z = -0.25;
  toolLink.add(gripperRight);

  const cameraLink = new THREE.Group();
  cameraLink.name = 'camera_link';
  cameraLink.position.set(-0.8, 4.0, 0.9);
  shoulderLink.add(cameraLink);

  const cameraBody = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.8, 1.0));
  cameraBody.name = 'camera_body';
  cameraLink.add(cameraBody);

  const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.5, 16));
  lens.name = 'camera_lens';
  lens.rotation.x = Math.PI / 2;
  lens.position.set(0, 0, 0.7);
  cameraLink.add(lens);

  return root;
}
