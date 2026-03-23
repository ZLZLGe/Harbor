import * as THREE from 'three';

export function createScene() {
  const root = new THREE.Group();

  const railFrame = new THREE.Group();
  railFrame.name = 'rail_frame';
  railFrame.position.set(0.0, 1.2, 0.0);
  root.add(railFrame);

  const beam = new THREE.Mesh(
    new THREE.BoxGeometry(2.4, 0.12, 0.18),
    new THREE.MeshBasicMaterial()
  );
  beam.name = 'beam';
  railFrame.add(beam);

  const hanger = new THREE.Mesh(
    new THREE.CylinderGeometry(0.03, 0.03, 0.9, 16),
    new THREE.MeshBasicMaterial()
  );
  hanger.name = 'hanger';
  hanger.position.set(-0.8, -0.45, 0.0);
  railFrame.add(hanger);

  const sensorBracket = new THREE.Group();
  sensorBracket.name = 'sensor_bracket';
  sensorBracket.position.set(0.75, -0.08, 0.12);
  sensorBracket.rotation.z = Math.PI / 18;
  railFrame.add(sensorBracket);

  const bracketPlate = new THREE.Mesh(
    new THREE.BoxGeometry(0.3, 0.1, 0.2),
    new THREE.MeshBasicMaterial()
  );
  bracketPlate.name = 'bracket_plate';
  sensorBracket.add(bracketPlate);

  const scannerHead = new THREE.Group();
  scannerHead.name = 'scanner_head';
  scannerHead.position.set(0.18, -0.18, 0.0);
  sensorBracket.add(scannerHead);

  const scannerBody = new THREE.Mesh(
    new THREE.BoxGeometry(0.22, 0.16, 0.18),
    new THREE.MeshBasicMaterial()
  );
  scannerBody.name = 'scanner_body';
  scannerHead.add(scannerBody);

  const lens = new THREE.Mesh(
    new THREE.CylinderGeometry(0.05, 0.05, 0.05, 18),
    new THREE.MeshBasicMaterial()
  );
  lens.name = 'scanner_lens';
  lens.position.set(0.11, 0.0, 0.0);
  lens.rotation.z = Math.PI / 2;
  scannerHead.add(lens);

  const powerBox = new THREE.Group();
  powerBox.name = 'power_box';
  powerBox.position.set(-0.45, -0.16, -0.14);
  railFrame.add(powerBox);

  const enclosure = new THREE.Mesh(
    new THREE.BoxGeometry(0.34, 0.24, 0.24),
    new THREE.MeshBasicMaterial()
  );
  enclosure.name = 'enclosure';
  powerBox.add(enclosure);

  return root;
}
