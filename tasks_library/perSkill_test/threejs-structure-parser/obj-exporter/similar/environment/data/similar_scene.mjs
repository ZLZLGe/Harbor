import * as THREE from "three";

function makeBeam(length, radius, name) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 16));
  mesh.name = name;
  return mesh;
}

export function createScene() {
  const root = new THREE.Group();
  root.name = "inspection_tower";

  const towerBase = new THREE.Group();
  towerBase.name = "tower_base";
  root.add(towerBase);

  const footing = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.45, 4.0));
  footing.name = "footing_pad";
  footing.position.set(0, 0.225, 0);
  towerBase.add(footing);

  const platform = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.2, 2.2));
  platform.name = "service_platform";
  platform.position.set(0, 2.5, 0);
  towerBase.add(platform);

  const legOffsets = [
    [-1.5, 1.35, -1.2],
    [1.5, 1.35, -1.2],
    [-1.5, 1.35, 1.2],
    [1.5, 1.35, 1.2]
  ];
  legOffsets.forEach(([x, y, z], index) => {
    const leg = makeBeam(2.7, 0.11, `tower_leg_${index + 1}`);
    leg.position.set(x, y, z);
    towerBase.add(leg);
  });

  const braceCluster = new THREE.Group();
  braceCluster.position.set(0, 1.35, 0);
  towerBase.add(braceCluster);

  const frontBrace = makeBeam(3.25, 0.06, "front_brace");
  frontBrace.rotation.z = Math.PI / 4;
  frontBrace.position.set(0, 0, 1.2);
  braceCluster.add(frontBrace);

  const rearBrace = makeBeam(3.25, 0.06, "rear_brace");
  rearBrace.rotation.z = -Math.PI / 4;
  rearBrace.position.set(0, 0, -1.2);
  braceCluster.add(rearBrace);

  const sensorRing = new THREE.Group();
  sensorRing.name = "sensor_ring";
  sensorRing.position.set(0, 4.0, 0);
  sensorRing.rotation.y = Math.PI / 6;
  root.add(sensorRing);

  const centerHub = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.7, 20));
  centerHub.name = "center_hub";
  centerHub.rotation.z = Math.PI / 2;
  sensorRing.add(centerHub);

  const outerRing = new THREE.Mesh(new THREE.TorusGeometry(1.6, 0.12, 12, 48));
  outerRing.name = "outer_ring";
  outerRing.rotation.y = Math.PI / 2;
  sensorRing.add(outerRing);

  const podFrame = new THREE.Group();
  sensorRing.add(podFrame);

  [
    { angle: 0, name: "sensor_pod_north" },
    { angle: (2 * Math.PI) / 3, name: "sensor_pod_west" },
    { angle: (4 * Math.PI) / 3, name: "sensor_pod_east" }
  ].forEach(({ angle, name }) => {
    const pod = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.28, 0.28));
    pod.name = name;
    pod.position.set(Math.cos(angle) * 1.55, Math.sin(angle) * 1.55, 0);
    pod.lookAt(0, 0, 0);
    podFrame.add(pod);
  });

  const serviceCart = new THREE.Group();
  serviceCart.name = "service_cart";
  serviceCart.position.set(3.4, 0.42, -2.2);
  serviceCart.rotation.y = -Math.PI / 5;
  root.add(serviceCart);

  const chassis = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.28, 0.92));
  chassis.name = "cart_chassis";
  chassis.position.set(0, 0.25, 0);
  serviceCart.add(chassis);

  const mast = makeBeam(1.4, 0.08, "cart_mast");
  mast.position.set(-0.45, 0.95, 0);
  serviceCart.add(mast);

  const boom = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.12, 0.18));
  boom.name = "inspection_boom";
  boom.position.set(0.05, 1.55, 0);
  boom.rotation.z = -0.45;
  serviceCart.add(boom);

  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16));
  lamp.name = "inspection_lamp";
  lamp.position.set(0.58, 1.78, 0);
  serviceCart.add(lamp);

  return root;
}
