import * as THREE from "three";

export function createScene() {
  const root = new THREE.Group();
  root.name = "inspection_lamp";

  const baseFrame = new THREE.Group();
  baseFrame.name = "base_frame";
  root.add(baseFrame);

  const baseDisc = new THREE.Mesh(new THREE.CylinderGeometry(3.4, 3.8, 0.9, 28));
  baseDisc.position.set(0, 0.45, 0);
  baseFrame.add(baseDisc);

  const badgeRig = new THREE.Group();
  badgeRig.position.set(1.7, 0.7, -0.9);
  badgeRig.rotation.y = Math.PI / 6;
  badgeRig.scale.set(1.2, 0.55, -0.8);
  baseFrame.add(badgeRig);

  const badgeTilt = new THREE.Group();
  badgeTilt.rotation.x = -Math.PI / 11;
  badgeTilt.rotation.z = Math.PI / 15;
  badgeRig.add(badgeTilt);

  const badge = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.22, 0.45));
  badge.position.set(0, 0.12, 0);
  badgeTilt.add(badge);

  const lampHead = new THREE.Group();
  lampHead.name = "lamp_head";
  lampHead.position.set(0.4, 6.2, -0.6);
  lampHead.rotation.z = Math.PI / 7;
  root.add(lampHead);

  const shellRig = new THREE.Group();
  shellRig.rotation.x = Math.PI / 10;
  shellRig.scale.set(1.0, 1.15, 0.9);
  lampHead.add(shellRig);

  const shell = new THREE.Mesh(new THREE.BoxGeometry(2.4, 1.4, 1.8));
  shell.position.set(0, 0, 0.2);
  shellRig.add(shell);

  const diffuser = new THREE.Mesh(new THREE.ConeGeometry(0.65, 0.9, 18));
  diffuser.rotation.x = -Math.PI / 2;
  diffuser.position.set(0, -0.1, 1.2);
  shellRig.add(diffuser);

  const handleRing = new THREE.Group();
  handleRing.name = "handle_ring";
  handleRing.position.set(0, 0.9, 0.3);
  handleRing.rotation.y = Math.PI / 8;
  shellRig.add(handleRing);

  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.8, 0.1, 12, 36));
  ring.rotation.x = Math.PI / 2;
  handleRing.add(ring);

  const screwGeometry = new THREE.CylinderGeometry(0.05, 0.05, 0.32, 10);
  const screwMaterial = new THREE.MeshBasicMaterial();
  const screws = new THREE.InstancedMesh(screwGeometry, screwMaterial, 3);
  screws.name = "handle_screws";
  const temp = new THREE.Object3D();
  [
    [0.72, 0.0, 0.0],
    [-0.36, 0.62, 0.0],
    [-0.36, -0.62, 0.0]
  ].forEach((position, index) => {
    temp.position.set(position[0], position[1], position[2]);
    temp.rotation.z = Math.PI / 2;
    temp.updateMatrix();
    screws.setMatrixAt(index, temp.matrix);
  });
  screws.instanceMatrix.needsUpdate = true;
  handleRing.add(screws);

  const counterweight = new THREE.Group();
  counterweight.name = "counterweight";
  counterweight.position.set(-2.3, 4.6, -1.4);
  counterweight.rotation.y = -Math.PI / 9;
  root.add(counterweight);

  const counterweightMesh = new THREE.Mesh(new THREE.SphereGeometry(0.95, 20, 14));
  counterweightMesh.scale.set(1.1, 0.8, 1.4);
  counterweightMesh.position.set(0, 0.15, 0);
  counterweight.add(counterweightMesh);

  const serviceCluster = new THREE.Group();
  serviceCluster.name = "service_cluster";
  serviceCluster.position.set(1.8, 3.2, 1.6);
  serviceCluster.rotation.y = Math.PI / 5;
  root.add(serviceCluster);

  const indicatorTabs = new THREE.Group();
  indicatorTabs.name = "indicator_tabs";
  indicatorTabs.position.set(0.2, 0.4, 0.3);
  serviceCluster.add(indicatorTabs);

  const tabGeometry = new THREE.BoxGeometry(0.3, 0.08, 0.45);
  const tabMaterial = new THREE.MeshBasicMaterial();
  const tabs = new THREE.InstancedMesh(tabGeometry, tabMaterial, 2);
  tabs.name = "indicator_tab_instances";
  [
    [-0.18, 0.0, 0.0],
    [0.18, 0.06, 0.14]
  ].forEach((position, index) => {
    temp.position.set(position[0], position[1], position[2]);
    temp.rotation.x = index === 0 ? 0 : Math.PI / 12;
    temp.rotation.y = index === 0 ? 0 : -Math.PI / 10;
    temp.updateMatrix();
    tabs.setMatrixAt(index, temp.matrix);
  });
  tabs.instanceMatrix.needsUpdate = true;
  indicatorTabs.add(tabs);

  return root;
}
