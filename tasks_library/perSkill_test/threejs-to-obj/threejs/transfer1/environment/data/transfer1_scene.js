import * as THREE from "three";

export function createScene() {
  const root = new THREE.Group();
  root.name = "archive_trolley";

  const baseCart = new THREE.Group();
  baseCart.name = "base_cart";
  root.add(baseCart);

  const deck = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.35, 2.4));
  deck.position.set(0, 0.175, 0);
  baseCart.add(deck);

  const wheelCarrier = new THREE.Group();
  wheelCarrier.position.set(0, -0.2, 0);
  baseCart.add(wheelCarrier);

  const wheelGeometry = new THREE.CylinderGeometry(0.28, 0.28, 0.18, 14);
  const wheelMaterial = new THREE.MeshBasicMaterial();
  const wheels = new THREE.InstancedMesh(wheelGeometry, wheelMaterial, 4);
  wheels.name = "wheel_instances";
  const temp = new THREE.Object3D();
  [
    [-1.7, 0, -0.95],
    [-1.7, 0, 0.95],
    [1.7, 0, -0.95],
    [1.7, 0, 0.95]
  ].forEach((position, index) => {
    temp.position.set(position[0], position[1], position[2]);
    temp.rotation.z = Math.PI / 2;
    temp.updateMatrix();
    wheels.setMatrixAt(index, temp.matrix);
  });
  wheels.instanceMatrix.needsUpdate = true;
  wheelCarrier.add(wheels);

  const drawerBank = new THREE.Group();
  drawerBank.name = "drawer_bank";
  drawerBank.position.set(0.2, 1.1, 0);
  baseCart.add(drawerBank);

  const drawerBody = new THREE.Mesh(new THREE.BoxGeometry(2.2, 1.5, 1.3));
  drawerBody.position.set(0, 0.75, 0);
  drawerBank.add(drawerBody);

  const labelTabs = new THREE.Group();
  labelTabs.name = "label_tabs";
  labelTabs.position.set(1.15, 0.95, 0);
  drawerBank.add(labelTabs);

  const tabGeometry = new THREE.BoxGeometry(0.12, 0.18, 0.4);
  const tabMaterial = new THREE.MeshBasicMaterial();
  const tabs = new THREE.InstancedMesh(tabGeometry, tabMaterial, 3);
  tabs.name = "tab_instances";
  [
    [0, 0.35, -0.35],
    [0.05, 0.0, 0.0],
    [0.02, -0.35, 0.35]
  ].forEach((position, index) => {
    temp.position.set(position[0], position[1], position[2]);
    temp.rotation.y = index === 1 ? Math.PI / 10 : 0;
    temp.updateMatrix();
    tabs.setMatrixAt(index, temp.matrix);
  });
  tabs.instanceMatrix.needsUpdate = true;
  labelTabs.add(tabs);

  const crateStack = new THREE.Group();
  crateStack.name = "crate_stack";
  crateStack.position.set(-2.8, 0.4, -3.2);
  root.add(crateStack);

  const lowerCrate = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.7, 1.4));
  lowerCrate.position.set(0, 0.35, 0);
  crateStack.add(lowerCrate);

  const upperCrate = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.5, 1.0));
  upperCrate.position.set(0.1, 0.95, 0.1);
  upperCrate.rotation.y = Math.PI / 14;
  crateStack.add(upperCrate);

  const sensorPole = new THREE.Group();
  sensorPole.name = "sensor_pole";
  sensorPole.position.set(2.9, 0, 2.7);
  root.add(sensorPole);

  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 3.4, 16));
  pole.position.set(0, 1.7, 0);
  sensorPole.add(pole);

  const sensorHead = new THREE.Mesh(new THREE.SphereGeometry(0.35, 16, 10));
  sensorHead.position.set(0.2, 3.45, 0.05);
  sensorPole.add(sensorHead);

  const serviceLoop = new THREE.Group();
  serviceLoop.name = "service_loop";
  serviceLoop.position.set(2.2, 2.6, -1.8);
  root.add(serviceLoop);

  const tiePoints = new THREE.Group();
  tiePoints.name = "tie_points";
  tiePoints.position.set(0.1, 0.4, 0);
  serviceLoop.add(tiePoints);

  const ringGeometry = new THREE.TorusGeometry(0.18, 0.03, 10, 20);
  const rings = new THREE.InstancedMesh(ringGeometry, wheelMaterial, 2);
  rings.name = "tie_ring_instances";
  [
    [-0.25, 0, 0],
    [0.25, 0.15, 0.08]
  ].forEach((position, index) => {
    temp.position.set(position[0], position[1], position[2]);
    temp.rotation.x = Math.PI / 2;
    temp.rotation.z = index === 0 ? 0 : Math.PI / 8;
    temp.updateMatrix();
    rings.setMatrixAt(index, temp.matrix);
  });
  rings.instanceMatrix.needsUpdate = true;
  tiePoints.add(rings);

  return root;
}
