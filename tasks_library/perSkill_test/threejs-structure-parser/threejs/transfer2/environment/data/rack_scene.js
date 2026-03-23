import * as THREE from 'three';

function setInstanceTransforms(mesh, transforms) {
  const matrix = new THREE.Matrix4();
  transforms.forEach((transform, index) => {
    matrix.compose(
      new THREE.Vector3(...transform.position),
      new THREE.Quaternion().setFromEuler(new THREE.Euler(...transform.rotation)),
      new THREE.Vector3(...transform.scale),
    );
    mesh.setMatrixAt(index, matrix);
  });
  mesh.instanceMatrix.needsUpdate = true;
}

export function createScene() {
  const root = new THREE.Group();
  root.name = 'warehouse_layout';

  const bayAlpha = new THREE.Group();
  bayAlpha.name = 'bay_alpha';
  root.add(bayAlpha);

  const crateGeometry = new THREE.BoxGeometry(1.2, 1.0, 1.0);
  const crateMesh = new THREE.InstancedMesh(crateGeometry, new THREE.MeshBasicMaterial(), 3);
  crateMesh.name = 'crate_stack';
  setInstanceTransforms(crateMesh, [
    { position: [-2.0, 0.5, -1.0], rotation: [0, 0, 0], scale: [1, 1, 1] },
    { position: [-2.0, 0.5, 0.5], rotation: [0, Math.PI / 12, 0], scale: [1, 1, 1] },
    { position: [-2.0, 1.7, 0.5], rotation: [0, Math.PI / 12, 0], scale: [1, 1, 1] },
  ]);
  bayAlpha.add(crateMesh);

  const palletGeometry = new THREE.BoxGeometry(1.4, 0.18, 1.1);
  const palletMesh = new THREE.InstancedMesh(palletGeometry, new THREE.MeshBasicMaterial(), 2);
  palletMesh.name = 'pallet_row';
  setInstanceTransforms(palletMesh, [
    { position: [-2.0, 0.09, -1.0], rotation: [0, 0, 0], scale: [1, 1, 1] },
    { position: [-2.0, 0.09, 0.5], rotation: [0, 0, 0], scale: [1, 1, 1] },
  ]);
  bayAlpha.add(palletMesh);

  const bayBeta = new THREE.Group();
  bayBeta.name = 'bay_beta';
  bayBeta.position.set(3.4, 0, 0);
  root.add(bayBeta);

  const drumGeometry = new THREE.CylinderGeometry(0.45, 0.45, 1.2, 18);
  const drumMesh = new THREE.InstancedMesh(drumGeometry, new THREE.MeshBasicMaterial(), 4);
  drumMesh.name = 'drum_cluster';
  setInstanceTransforms(drumMesh, [
    { position: [0.0, 0.6, -1.5], rotation: [0, 0, 0], scale: [1, 1, 1] },
    { position: [0.9, 0.6, -1.5], rotation: [0, Math.PI / 6, 0], scale: [1, 1, 1] },
    { position: [0.0, 0.6, -0.4], rotation: [0, Math.PI / 10, 0], scale: [1, 1, 1] },
    { position: [0.9, 0.6, -0.4], rotation: [0, 0, 0], scale: [1, 1, 1] },
  ]);
  bayBeta.add(drumMesh);

  const inspectionStation = new THREE.Group();
  inspectionStation.name = 'inspection_station';
  inspectionStation.position.set(0.2, 0, 2.1);
  bayBeta.add(inspectionStation);

  const caseGeometry = new THREE.BoxGeometry(0.9, 0.7, 0.9);
  const caseMesh = new THREE.InstancedMesh(caseGeometry, new THREE.MeshBasicMaterial(), 2);
  caseMesh.name = 'inspection_case';
  setInstanceTransforms(caseMesh, [
    { position: [0.0, 0.35, 0.0], rotation: [0, 0, 0], scale: [1, 1, 1] },
    { position: [1.0, 0.35, 0.2], rotation: [0, -Math.PI / 8, 0], scale: [1, 1, 1] },
  ]);
  inspectionStation.add(caseMesh);

  const serviceCart = new THREE.Group();
  serviceCart.name = 'service_cart';
  serviceCart.position.set(-1.2, 0, 3.8);
  root.add(serviceCart);

  const toteGeometry = new THREE.BoxGeometry(0.7, 0.45, 0.5);
  const toteMesh = new THREE.InstancedMesh(toteGeometry, new THREE.MeshBasicMaterial(), 3);
  toteMesh.name = 'tote_bin';
  setInstanceTransforms(toteMesh, [
    { position: [0.0, 0.5, 0.0], rotation: [0, 0, 0], scale: [1, 1, 1] },
    { position: [0.85, 0.5, 0.0], rotation: [0, Math.PI / 16, 0], scale: [1, 1, 1] },
    { position: [1.7, 0.5, 0.0], rotation: [0, 0, 0], scale: [1, 1, 1] },
  ]);
  serviceCart.add(toteMesh);

  return root;
}
