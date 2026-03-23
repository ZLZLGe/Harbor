import * as THREE from 'three';

function createBeam(start, end, radius, name) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();
  const geometry = new THREE.CylinderGeometry(radius, radius, length, 16);
  const mesh = new THREE.Mesh(geometry);
  mesh.name = name;
  mesh.position.copy(start).add(direction.clone().multiplyScalar(0.5));
  mesh.quaternion.setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    direction.clone().normalize(),
  );
  return mesh;
}

export function createScene() {
  const root = new THREE.Group();
  root.name = 'observation_ride';

  const supportFrame = new THREE.Group();
  supportFrame.name = 'support_frame';
  root.add(supportFrame);

  const platform = new THREE.Mesh(new THREE.BoxGeometry(16, 1.5, 14));
  platform.name = 'platform';
  platform.position.set(0, 0.75, 0);
  supportFrame.add(platform);

  const leftBeam = createBeam(
    new THREE.Vector3(-5, 1.5, 3),
    new THREE.Vector3(0, 16, 0),
    0.45,
    'left_support',
  );
  const rightBeam = createBeam(
    new THREE.Vector3(5, 1.5, 3),
    new THREE.Vector3(0, 16, 0),
    0.45,
    'right_support',
  );
  const backBeam = createBeam(
    new THREE.Vector3(0, 1.5, -4),
    new THREE.Vector3(0, 16, 0),
    0.45,
    'rear_support',
  );
  supportFrame.add(leftBeam, rightBeam, backBeam);

  const axleHousing = new THREE.Mesh(new THREE.BoxGeometry(4, 1.2, 3.6));
  axleHousing.name = 'axle_housing';
  axleHousing.position.set(0, 16, 0);
  supportFrame.add(axleHousing);

  const rotorFrame = new THREE.Group();
  rotorFrame.name = 'rotor_frame';
  rotorFrame.position.set(0, 16, 0);
  root.add(rotorFrame);

  const hub = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.2, 4, 24));
  hub.name = 'hub';
  hub.rotation.z = Math.PI / 2;
  rotorFrame.add(hub);

  const rim = new THREE.Mesh(new THREE.TorusGeometry(10, 0.6, 12, 48));
  rim.name = 'rim';
  rim.rotation.y = Math.PI / 2;
  rotorFrame.add(rim);

  for (let i = 0; i < 8; i += 1) {
    const angle = (i / 8) * Math.PI * 2;
    const spoke = createBeam(
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, Math.sin(angle) * 10, Math.cos(angle) * 10),
      0.15,
      `spoke_${i}`,
    );
    rotorFrame.add(spoke);
  }

  const cabins = [
    ['cabin_north', 0],
    ['cabin_east', Math.PI / 2],
    ['cabin_south', Math.PI],
    ['cabin_west', (Math.PI * 3) / 2],
  ];

  for (const [name, angle] of cabins) {
    const cabin = new THREE.Group();
    cabin.name = name;
    cabin.position.set(0, Math.sin(angle) * 10, Math.cos(angle) * 10);
    rotorFrame.add(cabin);

    const arm = createBeam(
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, -1.5, 0),
      0.08,
      `${name}_arm`,
    );
    cabin.add(arm);

    const body = new THREE.Mesh(new THREE.BoxGeometry(2.4, 1.8, 1.8));
    body.name = `${name}_body`;
    body.position.set(0, -2.6, 0);
    cabin.add(body);

    const canopy = new THREE.Mesh(new THREE.ConeGeometry(1.45, 0.7, 4));
    canopy.name = `${name}_canopy`;
    canopy.position.set(0, -1.5, 0);
    canopy.rotation.y = Math.PI / 4;
    cabin.add(canopy);
  }

  return root;
}
