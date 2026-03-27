import * as THREE from "three";

export function createScene() {
  const root = new THREE.Group();
  root.name = "packline_fixture";

  const rackFrame = new THREE.Group();
  rackFrame.name = "rack_frame";
  root.add(rackFrame);

  const leftBeam = new THREE.Mesh(new THREE.BoxGeometry(0.22, 3.0, 0.22));
  leftBeam.position.set(-1.45, 1.5, 0);
  rackFrame.add(leftBeam);

  const rightBeam = new THREE.Mesh(new THREE.BoxGeometry(0.22, 3.0, 0.22));
  rightBeam.position.set(1.45, 1.5, 0);
  rackFrame.add(rightBeam);

  const topBrace = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.18, 0.28));
  topBrace.position.set(0, 3.08, 0);
  rackFrame.add(topBrace);

  const sensorPods = new THREE.Group();
  sensorPods.name = "sensor_pods";
  sensorPods.position.set(1.25, 2.15, 0.45);
  sensorPods.rotation.y = Math.PI / 6;
  rackFrame.add(sensorPods);

  const podShell = new THREE.Mesh(new THREE.SphereGeometry(0.24, 16, 10));
  sensorPods.add(podShell);

  const podHorn = new THREE.Mesh(new THREE.ConeGeometry(0.1, 0.28, 14));
  podHorn.rotation.z = -Math.PI / 2;
  podHorn.position.set(0.28, 0.0, 0.0);
  sensorPods.add(podHorn);

  const binCarrier = new THREE.Group();
  binCarrier.name = "bin_carrier";
  binCarrier.position.set(0.25, 1.35, -1.55);
  binCarrier.rotation.z = -Math.PI / 12;
  binCarrier.scale.set(1.0, 0.8, -1.1);
  root.add(binCarrier);

  const carrierBody = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.32, 1.1));
  carrierBody.position.set(0, 0, 0);
  binCarrier.add(carrierBody);

  const barcodeBrackets = new THREE.Group();
  barcodeBrackets.name = "barcode_brackets";
  barcodeBrackets.position.set(1.08, 0.3, 0);
  binCarrier.add(barcodeBrackets);

  const bracketGeometry = new THREE.BoxGeometry(0.18, 0.24, 0.08);
  const bracketMaterial = new THREE.MeshBasicMaterial();
  const brackets = new THREE.InstancedMesh(bracketGeometry, bracketMaterial, 2);
  brackets.name = "barcode_bracket_instances";
  const temp = new THREE.Object3D();
  [
    [0, 0.18, -0.34],
    [0.03, -0.16, 0.34]
  ].forEach((position, index) => {
    temp.position.set(position[0], position[1], position[2]);
    temp.rotation.y = index === 0 ? 0 : Math.PI / 10;
    temp.updateMatrix();
    brackets.setMatrixAt(index, temp.matrix);
  });
  brackets.instanceMatrix.needsUpdate = true;
  barcodeBrackets.add(brackets);

  const rollerBank = new THREE.Group();
  rollerBank.name = "roller_bank";
  rollerBank.position.set(-0.15, 0.82, 1.85);
  root.add(rollerBank);

  const rollerGeometry = new THREE.CylinderGeometry(0.1, 0.1, 1.6, 14);
  const rollerMaterial = new THREE.MeshBasicMaterial();
  const rollers = new THREE.InstancedMesh(rollerGeometry, rollerMaterial, 4);
  rollers.name = "roller_instances";
  [
    [-0.9, 0, 0],
    [-0.3, 0.03, 0],
    [0.3, -0.02, 0],
    [0.9, 0.01, 0]
  ].forEach((position, index) => {
    temp.position.set(position[0], position[1], position[2]);
    temp.rotation.z = Math.PI / 2;
    temp.updateMatrix();
    rollers.setMatrixAt(index, temp.matrix);
  });
  rollers.instanceMatrix.needsUpdate = true;
  rollerBank.add(rollers);

  const serviceLoop = new THREE.Group();
  serviceLoop.name = "service_loop";
  serviceLoop.position.set(-1.8, 2.2, -1.2);
  root.add(serviceLoop);

  const tieClips = new THREE.Group();
  tieClips.name = "tie_clips";
  tieClips.position.set(0.15, 0.2, 0.0);
  serviceLoop.add(tieClips);

  const clipGeometry = new THREE.TorusGeometry(0.16, 0.025, 10, 20);
  const clips = new THREE.InstancedMesh(clipGeometry, rollerMaterial, 2);
  clips.name = "clip_instances";
  [
    [-0.22, 0.0, 0.0],
    [0.24, 0.14, 0.06]
  ].forEach((position, index) => {
    temp.position.set(position[0], position[1], position[2]);
    temp.rotation.x = Math.PI / 2;
    temp.rotation.z = index === 0 ? 0 : Math.PI / 7;
    temp.updateMatrix();
    clips.setMatrixAt(index, temp.matrix);
  });
  clips.instanceMatrix.needsUpdate = true;
  tieClips.add(clips);

  return root;
}
