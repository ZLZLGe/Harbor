import * as THREE from 'three';

export function createScene() {
  const root = new THREE.Group();
  root.name = 'staged_display';

  const material = new THREE.MeshBasicMaterial();

  const displayBase = new THREE.Group();
  displayBase.name = 'display_base';
  root.add(displayBase);

  const platform = new THREE.Mesh(
    new THREE.CylinderGeometry(3.4, 3.8, 0.7, 40),
    material,
  );
  platform.name = 'platform';
  platform.position.set(0, 0.35, 0);
  displayBase.add(platform);

  const riser = new THREE.Mesh(
    new THREE.CylinderGeometry(0.45, 0.55, 4.6, 28),
    material,
  );
  riser.name = 'riser';
  riser.position.set(0, 2.65, 0);
  displayBase.add(riser);

  const armJoint = new THREE.Group();
  armJoint.name = 'arm_joint';
  armJoint.position.set(0, 4.9, 0);
  armJoint.rotation.z = -Math.PI / 9;
  displayBase.add(armJoint);

  const arm = new THREE.Mesh(
    new THREE.BoxGeometry(0.55, 3.4, 0.45),
    material,
  );
  arm.name = 'arm';
  arm.position.set(0.2, 1.6, 0);
  armJoint.add(arm);

  const headMount = new THREE.Group();
  headMount.name = 'head_mount';
  headMount.position.set(0.6, 3.2, 0);
  headMount.rotation.y = Math.PI / 5;
  headMount.rotation.x = Math.PI / 14;
  armJoint.add(headMount);

  const head = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.9, 1.5, 6, 12),
    material,
  );
  head.name = 'head';
  head.scale.set(1.15, 0.9, 1.55);
  head.position.set(0.35, 0.2, 0);
  headMount.add(head);

  const diffuser = new THREE.Mesh(
    new THREE.CircleGeometry(0.72, 24),
    material,
  );
  diffuser.name = 'diffuser';
  diffuser.position.set(0.8, 0.15, 0);
  diffuser.rotation.y = Math.PI / 2;
  headMount.add(diffuser);

  const placardRig = new THREE.Group();
  placardRig.name = 'placard_rig';
  placardRig.position.set(1.6, 1.2, -1.1);
  placardRig.rotation.y = Math.PI / 7;
  placardRig.scale.set(1.25, 0.6, -0.85);
  displayBase.add(placardRig);

  const placardTilt = new THREE.Group();
  placardTilt.name = 'placard_tilt';
  placardTilt.rotation.x = -Math.PI / 10;
  placardTilt.rotation.z = Math.PI / 15;
  placardTilt.scale.set(0.95, 1.2, 1.05);
  placardRig.add(placardTilt);

  const placard = new THREE.Mesh(
    new THREE.BoxGeometry(2.4, 0.28, 0.9),
    material,
  );
  placard.name = 'placard';
  placard.position.set(0, 0.1, 0);
  placardTilt.add(placard);

  const fastenerGroup = new THREE.Group();
  fastenerGroup.name = 'fastener_group';
  fastenerGroup.position.set(0, 0.78, 0);
  displayBase.add(fastenerGroup);

  const fastenerGeometry = new THREE.CylinderGeometry(0.1, 0.1, 0.18, 16);
  const fastenerMesh = new THREE.InstancedMesh(fastenerGeometry, material, 4);
  fastenerMesh.name = 'fasteners';

  const offsets = [
    [-1.9, 0, -1.7],
    [1.9, 0, -1.7],
    [-1.9, 0, 1.7],
    [1.9, 0, 1.7],
  ];
  const temp = new THREE.Object3D();
  offsets.forEach(([x, y, z], index) => {
    temp.position.set(x, y, z);
    temp.rotation.x = Math.PI / 2;
    temp.updateMatrix();
    fastenerMesh.setMatrixAt(index, temp.matrix);
  });
  fastenerMesh.instanceMatrix.needsUpdate = true;
  fastenerGroup.add(fastenerMesh);

  return root;
}
