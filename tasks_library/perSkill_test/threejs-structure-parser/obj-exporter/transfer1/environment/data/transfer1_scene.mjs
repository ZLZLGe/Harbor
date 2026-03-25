import * as THREE from "three";

function beam(length, radius, name) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 14));
  mesh.name = name;
  return mesh;
}

export function createScene() {
  const root = new THREE.Group();
  root.name = "greenhouse_pod";

  const frameModule = new THREE.Group();
  frameModule.name = "frame_module";
  root.add(frameModule);

  const baseFrame = new THREE.Mesh(new THREE.BoxGeometry(5.2, 0.25, 3.6));
  baseFrame.name = "base_frame";
  baseFrame.position.set(0, 0.125, 0);
  frameModule.add(baseFrame);

  const archLeft = beam(3.5, 0.08, "arch_left");
  archLeft.position.set(-1.6, 1.75, 0);
  archLeft.rotation.z = -0.35;
  frameModule.add(archLeft);

  const archRight = beam(3.5, 0.08, "arch_right");
  archRight.position.set(1.6, 1.75, 0);
  archRight.rotation.z = 0.35;
  frameModule.add(archRight);

  const ridgeBar = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.2, 3.3));
  ridgeBar.name = "ridge_bar";
  ridgeBar.position.set(0, 3.05, 0);
  frameModule.add(ridgeBar);

  const climateModule = new THREE.Group();
  climateModule.name = "climate_module";
  climateModule.position.set(0.7, 2.5, -1.35);
  climateModule.rotation.y = Math.PI / 7;
  root.add(climateModule);

  const fanHub = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.4, 20));
  fanHub.name = "fan_hub";
  fanHub.rotation.x = Math.PI / 2;
  climateModule.add(fanHub);

  const fanRing = new THREE.Mesh(new THREE.TorusGeometry(0.7, 0.08, 10, 40));
  fanRing.name = "fan_ring";
  fanRing.rotation.y = Math.PI / 2;
  climateModule.add(fanRing);

  const climateShell = new THREE.Group();
  climateModule.add(climateShell);

  const filterBox = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.5, 0.3));
  filterBox.name = "filter_box";
  filterBox.position.set(0, 0.85, 0);
  climateShell.add(filterBox);

  const waterModule = new THREE.Group();
  waterModule.name = "water_module";
  waterModule.position.set(-1.5, 0.4, 1.1);
  root.add(waterModule);

  const tank = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 1.4, 18));
  tank.name = "buffer_tank";
  tank.position.set(0, 0.7, 0);
  waterModule.add(tank);

  const pumpBox = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.45, 0.5));
  pumpBox.name = "pump_box";
  pumpBox.position.set(0.85, 0.3, 0.15);
  waterModule.add(pumpBox);

  const sprayArm = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.1, 0.1));
  sprayArm.name = "spray_arm";
  sprayArm.position.set(0.2, 1.3, -0.8);
  sprayArm.rotation.z = -0.2;
  waterModule.add(sprayArm);

  const catwalkModule = new THREE.Group();
  catwalkModule.name = "catwalk_module";
  catwalkModule.position.set(0, 1.2, 1.85);
  root.add(catwalkModule);

  const deck = new THREE.Mesh(new THREE.BoxGeometry(4.5, 0.12, 0.55));
  deck.name = "catwalk_deck";
  catwalkModule.add(deck);

  const railLeft = beam(4.5, 0.04, "rail_left");
  railLeft.position.set(0, 0.45, -0.18);
  railLeft.rotation.z = Math.PI / 2;
  catwalkModule.add(railLeft);

  const railRight = beam(4.5, 0.04, "rail_right");
  railRight.position.set(0, 0.45, 0.18);
  railRight.rotation.z = Math.PI / 2;
  catwalkModule.add(railRight);

  return root;
}
