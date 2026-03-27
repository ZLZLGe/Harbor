import * as THREE from "three";

export function createScene() {
  const root = new THREE.Group();
  root.name = "pallet_sorter";

  const baseLink = new THREE.Group();
  baseLink.name = "base_link";
  root.add(baseLink);

  const basePlate = new THREE.Mesh(new THREE.BoxGeometry(2.8, 0.4, 2.2));
  basePlate.position.set(0, 0.2, 0);
  baseLink.add(basePlate);

  const mastLink = new THREE.Group();
  mastLink.name = "mast_link";
  mastLink.position.set(0.5, 0.4, -0.2);
  baseLink.add(mastLink);

  const mastColumn = new THREE.Mesh(new THREE.BoxGeometry(0.45, 3.0, 0.55));
  mastColumn.position.set(0, 1.5, 0);
  mastLink.add(mastColumn);

  const forkSlide = new THREE.Group();
  forkSlide.name = "fork_slide";
  forkSlide.position.set(0.45, 1.0, 0.0);
  mastLink.add(forkSlide);

  const tineLeft = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.16, 0.18));
  tineLeft.position.set(0.7, 0, -0.28);
  forkSlide.add(tineLeft);

  const tineRight = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.16, 0.18));
  tineRight.position.set(0.7, 0, 0.28);
  forkSlide.add(tineRight);

  const sensorHinge = new THREE.Group();
  sensorHinge.name = "sensor_hinge";
  sensorHinge.position.set(-0.35, 2.45, 0.22);
  sensorHinge.rotation.z = Math.PI / 9;
  mastLink.add(sensorHinge);

  const hingeBarrel = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.7, 16));
  hingeBarrel.rotation.z = Math.PI / 2;
  sensorHinge.add(hingeBarrel);

  const sensorHead = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.35, 0.45));
  sensorHead.position.set(0.48, 0, 0.0);
  sensorHinge.add(sensorHead);

  const counterweightLink = new THREE.Group();
  counterweightLink.name = "counterweight_link";
  counterweightLink.position.set(-1.1, 0.95, 0.0);
  baseLink.add(counterweightLink);

  const counterweight = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.2, 1.2));
  counterweight.position.set(0, 0.6, 0);
  counterweightLink.add(counterweight);

  const cableGuide = new THREE.Group();
  cableGuide.name = "cable_guide";
  cableGuide.position.set(0.1, 2.1, -0.4);
  mastLink.add(cableGuide);

  const guideLoop = new THREE.Mesh(new THREE.TorusGeometry(0.18, 0.035, 10, 24));
  guideLoop.rotation.x = Math.PI / 2;
  cableGuide.add(guideLoop);

  return root;
}
