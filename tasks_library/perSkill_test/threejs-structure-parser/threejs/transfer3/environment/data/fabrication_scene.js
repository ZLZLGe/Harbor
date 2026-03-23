import * as THREE from 'three';

function makeMesh(name, geometry, color) {
  const mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({ color }),
  );
  mesh.name = name;
  return mesh;
}

export function createScene() {
  const root = new THREE.Group();

  const baseFrame = new THREE.Group();
  baseFrame.name = 'base_frame';
  baseFrame.position.set(-1.4, 0.35, 0.4);
  baseFrame.rotation.set(0.0, 0.18, 0.32);

  const basePlate = makeMesh(
    'base_plate',
    new THREE.BoxGeometry(2.8, 0.32, 1.45),
    0x566573,
  );
  basePlate.position.set(0.0, -0.08, 0.0);
  baseFrame.add(basePlate);

  const sideRail = makeMesh(
    'side_rail',
    new THREE.BoxGeometry(2.1, 0.18, 0.24),
    0x6d7b86,
  );
  sideRail.position.set(0.1, 0.42, -0.46);
  sideRail.rotation.y = 0.2;
  baseFrame.add(sideRail);

  const baseHelper = new THREE.Group();
  baseHelper.position.set(0.82, 0.48, 0.34);
  baseHelper.rotation.z = -0.16;
  baseFrame.add(baseHelper);

  const gusset = makeMesh(
    'gusset',
    new THREE.BoxGeometry(0.42, 0.62, 0.18),
    0x7c8b95,
  );
  gusset.position.set(-0.14, 0.06, 0.0);
  gusset.rotation.x = 0.24;
  baseHelper.add(gusset);

  const sensorMount = new THREE.Group();
  sensorMount.name = 'sensor_mount';
  sensorMount.position.set(0.5, 0.18, 0.08);
  sensorMount.rotation.set(0.22, 0.46, 0.0);
  baseHelper.add(sensorMount);

  const sensorPlate = makeMesh(
    'sensor_plate',
    new THREE.BoxGeometry(0.72, 0.14, 0.48),
    0x9aa7b1,
  );
  sensorPlate.position.set(0.0, 0.0, 0.0);
  sensorMount.add(sensorPlate);

  const wireGuide = makeMesh(
    'wire_guide',
    new THREE.TorusGeometry(0.14, 0.04, 10, 20),
    0xb6c0c8,
  );
  wireGuide.position.set(0.12, 0.16, 0.0);
  wireGuide.rotation.x = Math.PI / 2;
  sensorMount.add(wireGuide);

  const armature = new THREE.Group();
  armature.name = 'armature';
  armature.position.set(1.55, 1.12, -0.65);
  armature.rotation.set(0.24, -0.52, 0.15);

  const armBeam = makeMesh(
    'arm_beam',
    new THREE.BoxGeometry(1.36, 0.32, 0.42),
    0x5a6774,
  );
  armBeam.position.set(0.0, 0.0, 0.0);
  armature.add(armBeam);

  const elbowHousing = makeMesh(
    'elbow_housing',
    new THREE.CylinderGeometry(0.24, 0.24, 0.72, 18),
    0x77848f,
  );
  elbowHousing.position.set(-0.54, 0.1, 0.0);
  elbowHousing.rotation.z = Math.PI / 2;
  armature.add(elbowHousing);

  const conduitGroup = new THREE.Group();
  conduitGroup.position.set(0.44, 0.22, 0.08);
  conduitGroup.rotation.x = -0.18;
  armature.add(conduitGroup);

  const conduitTube = makeMesh(
    'conduit_tube',
    new THREE.CylinderGeometry(0.08, 0.08, 0.94, 16),
    0x90a0ab,
  );
  conduitTube.position.set(0.0, 0.0, 0.0);
  conduitTube.rotation.z = Math.PI / 2;
  conduitGroup.add(conduitTube);

  const endEffector = new THREE.Group();
  endEffector.name = 'end_effector';
  endEffector.position.set(0.96, 0.36, 0.28);
  endEffector.rotation.set(0.0, 0.12, -0.42);
  armature.add(endEffector);

  const jawLeft = makeMesh(
    'jaw_left',
    new THREE.BoxGeometry(0.54, 0.12, 0.18),
    0xb59b7a,
  );
  jawLeft.position.set(0.0, 0.12, 0.08);
  endEffector.add(jawLeft);

  const jawRight = makeMesh(
    'jaw_right',
    new THREE.BoxGeometry(0.54, 0.12, 0.18),
    0xb59b7a,
  );
  jawRight.position.set(0.0, -0.12, -0.08);
  endEffector.add(jawRight);

  const counterweight = new THREE.Group();
  counterweight.name = 'counterweight';
  counterweight.position.set(-0.18, 1.46, 1.18);
  counterweight.rotation.set(-0.2, 0.38, 0.18);

  const weightBlock = makeMesh(
    'weight_block',
    new THREE.BoxGeometry(0.9, 0.62, 0.74),
    0x636363,
  );
  weightBlock.position.set(0.0, 0.0, 0.0);
  counterweight.add(weightBlock);

  const anchorPin = makeMesh(
    'anchor_pin',
    new THREE.CylinderGeometry(0.12, 0.12, 1.02, 18),
    0x8f8f8f,
  );
  anchorPin.position.set(0.0, 0.0, 0.0);
  anchorPin.rotation.x = Math.PI / 2;
  counterweight.add(anchorPin);

  const emptyFixture = new THREE.Group();
  emptyFixture.name = 'empty_fixture';
  emptyFixture.position.set(2.4, 0.6, 1.1);

  root.add(baseFrame);
  root.add(armature);
  root.add(counterweight);
  root.add(emptyFixture);

  return root;
}
