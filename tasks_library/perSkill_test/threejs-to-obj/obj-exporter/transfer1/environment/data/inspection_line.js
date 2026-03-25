import * as THREE from "three";

export function createScene() {
  const root = new THREE.Group();
  root.name = "inspection_line";

  const conveyor = new THREE.Group();
  conveyor.name = "conveyor";
  root.add(conveyor);

  const deck = new THREE.Mesh(new THREE.BoxGeometry(9.5, 0.35, 2.2));
  deck.name = "deck";
  deck.position.set(0, 0.6, 0);
  conveyor.add(deck);

  const railLeft = new THREE.Mesh(new THREE.BoxGeometry(9.1, 0.24, 0.18));
  railLeft.position.set(0, 1.05, -0.92);
  conveyor.add(railLeft);

  const railRight = railLeft.clone();
  railRight.position.z = 0.92;
  conveyor.add(railRight);

  const supportGeometry = new THREE.BoxGeometry(0.18, 1.1, 0.18);
  const supportMaterial = new THREE.MeshBasicMaterial();
  const supports = new THREE.InstancedMesh(supportGeometry, supportMaterial, 6);
  supports.name = "supports";
  const helper = new THREE.Object3D();
  for (let index = 0; index < 6; index += 1) {
    helper.position.set(-3.8 + index * 1.52, 0.25, 0);
    helper.updateMatrix();
    supports.setMatrixAt(index, helper.matrix);
  }
  supports.instanceMatrix.needsUpdate = true;
  conveyor.add(supports);

  const inspectionFixture = new THREE.Group();
  inspectionFixture.name = "inspection_fixture";
  inspectionFixture.position.set(2.1, 1.45, 0.4);
  inspectionFixture.rotation.y = Math.PI / 5;
  inspectionFixture.rotation.x = Math.PI / 14;
  root.add(inspectionFixture);

  const cradle = new THREE.Group();
  cradle.name = "cradle";
  cradle.position.set(0, 0.4, 0);
  cradle.rotation.z = -Math.PI / 16;
  inspectionFixture.add(cradle);

  const baseBeam = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.28, 0.9));
  baseBeam.name = "base_beam";
  cradle.add(baseBeam);

  const rollers = new THREE.InstancedMesh(
    new THREE.CylinderGeometry(0.16, 0.16, 0.74, 18),
    new THREE.MeshBasicMaterial(),
    3,
  );
  rollers.name = "rollers";
  for (let index = 0; index < 3; index += 1) {
    helper.position.set(-0.72 + index * 0.72, 0.18, 0);
    helper.rotation.z = Math.PI / 2;
    helper.updateMatrix();
    rollers.setMatrixAt(index, helper.matrix);
  }
  rollers.instanceMatrix.needsUpdate = true;
  cradle.add(rollers);

  const sensorArch = new THREE.Group();
  sensorArch.name = "sensor_arch";
  sensorArch.position.set(0, 1.15, 0);
  sensorArch.rotation.z = Math.PI / 18;
  inspectionFixture.add(sensorArch);

  const arch = new THREE.Mesh(new THREE.TorusGeometry(1.05, 0.08, 16, 64, Math.PI));
  arch.name = "arch";
  arch.rotation.z = Math.PI;
  arch.rotation.x = Math.PI / 2;
  sensorArch.add(arch);

  const postGeometry = new THREE.BoxGeometry(0.12, 1.2, 0.16);
  const leftPost = new THREE.Mesh(postGeometry);
  leftPost.position.set(-1.04, -0.62, 0);
  sensorArch.add(leftPost);

  const rightPost = leftPost.clone();
  rightPost.position.x = 1.04;
  sensorArch.add(rightPost);

  const probeCluster = new THREE.Group();
  probeCluster.name = "probe_cluster";
  probeCluster.position.set(0.28, 0.1, 0.44);
  probeCluster.rotation.y = Math.PI / 7;
  sensorArch.add(probeCluster);

  const probeBody = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.5, 0.18));
  probeCluster.add(probeBody);

  const probeTip = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.24, 14));
  probeTip.position.set(0, -0.34, 0);
  probeCluster.add(probeTip);

  const safetyCage = new THREE.Mesh(new THREE.BoxGeometry(1.3, 1.8, 1.4));
  safetyCage.name = "safety_cage";
  safetyCage.position.set(-2.9, 1.15, 0);
  root.add(safetyCage);

  return root;
}
