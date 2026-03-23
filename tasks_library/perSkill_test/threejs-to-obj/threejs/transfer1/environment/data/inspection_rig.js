import * as THREE from 'three';

export function createScene() {
  const root = new THREE.Group();

  const basePlate = new THREE.Group();
  basePlate.name = 'base_plate';
  root.add(basePlate);

  const plate = new THREE.Mesh(
    new THREE.BoxGeometry(1.8, 0.12, 1.2),
    new THREE.MeshBasicMaterial()
  );
  plate.name = 'plate';
  plate.position.set(0.0, 0.06, 0.0);
  basePlate.add(plate);

  const mast = new THREE.Group();
  mast.name = 'mast';
  mast.position.set(-0.45, 0.12, -0.2);
  basePlate.add(mast);

  const pole = new THREE.Mesh(
    new THREE.CylinderGeometry(0.09, 0.09, 1.8, 20),
    new THREE.MeshBasicMaterial()
  );
  pole.name = 'pole';
  pole.position.set(0.0, 0.9, 0.0);
  mast.add(pole);

  const bracket = new THREE.Mesh(
    new THREE.BoxGeometry(0.34, 0.12, 0.28),
    new THREE.MeshBasicMaterial()
  );
  bracket.name = 'bracket';
  bracket.position.set(0.16, 1.55, 0.0);
  bracket.rotation.z = Math.PI / 10;
  mast.add(bracket);

  const sensorHead = new THREE.Group();
  sensorHead.name = 'sensor_head';
  sensorHead.position.set(0.28, 1.62, 0.0);
  sensorHead.rotation.y = Math.PI / 6;
  mast.add(sensorHead);

  const housing = new THREE.Mesh(
    new THREE.BoxGeometry(0.42, 0.24, 0.28),
    new THREE.MeshBasicMaterial()
  );
  housing.name = 'housing';
  sensorHead.add(housing);

  const lens = new THREE.Mesh(
    new THREE.CylinderGeometry(0.07, 0.07, 0.08, 20),
    new THREE.MeshBasicMaterial()
  );
  lens.name = 'lens';
  lens.position.set(0.18, 0.0, 0.0);
  lens.rotation.z = Math.PI / 2;
  sensorHead.add(lens);

  const cableGuide = new THREE.Group();
  cableGuide.name = 'cable_guide';
  cableGuide.position.set(-0.25, 0.92, 0.16);
  basePlate.add(cableGuide);

  const guide = new THREE.Mesh(
    new THREE.TorusGeometry(0.12, 0.03, 10, 24, Math.PI),
    new THREE.MeshBasicMaterial()
  );
  guide.name = 'guide';
  guide.rotation.y = Math.PI / 2;
  cableGuide.add(guide);

  return root;
}
