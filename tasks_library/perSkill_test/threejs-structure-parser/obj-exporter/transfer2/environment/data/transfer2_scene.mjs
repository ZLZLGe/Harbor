import * as THREE from "three";

function beam(length, radius, name) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 12));
  mesh.name = name;
  return mesh;
}

export function createScene() {
  const root = new THREE.Group();
  root.name = "shipyard_loader";

  const gantry = new THREE.Group();
  gantry.name = "gantry";
  root.add(gantry);

  const legLeft = beam(4.2, 0.12, "leg_left");
  legLeft.position.set(-2.0, 2.1, -1.2);
  gantry.add(legLeft);

  const legRight = beam(4.2, 0.12, "leg_right");
  legRight.position.set(2.0, 2.1, -1.2);
  gantry.add(legRight);

  const crossBar = new THREE.Mesh(new THREE.BoxGeometry(4.5, 0.25, 0.35));
  crossBar.name = "cross_bar";
  crossBar.position.set(0, 4.2, -1.2);
  gantry.add(crossBar);

  const trolley = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.4, 0.5));
  trolley.name = "trolley_block";
  trolley.position.set(0.9, 3.65, -1.2);
  gantry.add(trolley);

  const counterweight = new THREE.Group();
  counterweight.name = "counterweight";
  counterweight.position.set(-2.6, 0.7, 1.1);
  root.add(counterweight);

  const ballastBox = new THREE.Mesh(new THREE.BoxGeometry(1.5, 1.0, 1.1));
  ballastBox.name = "ballast_box";
  ballastBox.position.set(0, 0.5, 0);
  counterweight.add(ballastBox);

  const weightArm = new THREE.Mesh(new THREE.BoxGeometry(2.3, 0.18, 0.25));
  weightArm.name = "weight_arm";
  weightArm.position.set(1.25, 1.25, -0.2);
  weightArm.rotation.z = -0.22;
  counterweight.add(weightArm);

  const controlPod = new THREE.Group();
  controlPod.name = "control_pod";
  controlPod.position.set(1.8, 2.5, 0.7);
  controlPod.rotation.y = Math.PI / 5;
  root.add(controlPod);

  const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.8, 1.0));
  cabin.name = "operator_cabin";
  controlPod.add(cabin);

  const windowFrame = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.3, 0.12));
  windowFrame.name = "window_frame";
  windowFrame.position.set(0, 0.1, 0.5);
  controlPod.add(windowFrame);

  const antenna = beam(0.9, 0.04, "signal_antenna");
  antenna.position.set(-0.35, 0.85, 0);
  controlPod.add(antenna);

  const railBase = new THREE.Group();
  railBase.name = "rail_base";
  railBase.position.set(0, 0.12, 0);
  root.add(railBase);

  const railLeft = new THREE.Mesh(new THREE.BoxGeometry(5.5, 0.12, 0.2));
  railLeft.name = "rail_left";
  railLeft.position.set(0, 0, -1.6);
  railBase.add(railLeft);

  const railRight = new THREE.Mesh(new THREE.BoxGeometry(5.5, 0.12, 0.2));
  railRight.name = "rail_right";
  railRight.position.set(0, 0, 1.6);
  railBase.add(railRight);

  const sleeperGroup = new THREE.Group();
  railBase.add(sleeperGroup);
  for (let i = -2; i <= 2; i += 1) {
    const sleeper = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.1, 3.5));
    sleeper.name = `sleeper_${i + 3}`;
    sleeper.position.set(i * 1.1, -0.06, 0);
    sleeperGroup.add(sleeper);
  }

  return root;
}
