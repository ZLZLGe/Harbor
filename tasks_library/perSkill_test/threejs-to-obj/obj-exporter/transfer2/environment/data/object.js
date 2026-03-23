import * as THREE from 'three';

export function createScene() {
  const root = new THREE.Group();
  root.name = 'safety_barrier';
  root.rotation.y = Math.PI / 10;

  const material = new THREE.MeshBasicMaterial();

  const railGroup = new THREE.Group();
  railGroup.name = 'rail_group';
  root.add(railGroup);

  const lowerRail = new THREE.Mesh(
    new THREE.BoxGeometry(8.4, 0.16, 0.18),
    material,
  );
  lowerRail.name = 'lower_rail';
  lowerRail.position.set(0.4, 1.02, 0);
  railGroup.add(lowerRail);

  const upperRail = new THREE.Mesh(
    new THREE.BoxGeometry(8.4, 0.16, 0.18),
    material,
  );
  upperRail.name = 'upper_rail';
  upperRail.position.set(0.4, 1.68, 0);
  railGroup.add(upperRail);

  const posts = new THREE.InstancedMesh(
    new THREE.CylinderGeometry(0.12, 0.12, 1.95, 18),
    material,
    6,
  );
  posts.name = 'posts';
  const postPositions = [-3.6, -2.0, -0.4, 1.2, 2.8, 4.4];
  const temp = new THREE.Object3D();
  postPositions.forEach((x, index) => {
    temp.position.set(x, 0.98, 0);
    temp.rotation.set(0, 0, 0);
    temp.updateMatrix();
    posts.setMatrixAt(index, temp.matrix);
  });
  posts.instanceMatrix.needsUpdate = true;
  railGroup.add(posts);

  const feet = new THREE.InstancedMesh(
    new THREE.BoxGeometry(0.7, 0.12, 0.36),
    material,
    6,
  );
  feet.name = 'feet';
  postPositions.forEach((x, index) => {
    temp.position.set(x, 0.06, 0);
    temp.rotation.set(0, index % 2 === 0 ? 0 : Math.PI / 14, 0);
    temp.updateMatrix();
    feet.setMatrixAt(index, temp.matrix);
  });
  feet.instanceMatrix.needsUpdate = true;
  railGroup.add(feet);

  const warningPanelRig = new THREE.Group();
  warningPanelRig.name = 'warning_panel_rig';
  warningPanelRig.position.set(0.5, 1.38, -0.28);
  warningPanelRig.rotation.y = -Math.PI / 14;
  warningPanelRig.scale.set(1.05, 0.75, -0.82);
  railGroup.add(warningPanelRig);

  const warningPanel = new THREE.Mesh(
    new THREE.BoxGeometry(2.1, 0.72, 0.08),
    material,
  );
  warningPanel.name = 'warning_panel';
  warningPanelRig.add(warningPanel);

  const leftCap = new THREE.Group();
  leftCap.name = 'left_cap';
  leftCap.position.set(-3.95, 1.32, 0);
  leftCap.rotation.z = Math.PI / 14;
  railGroup.add(leftCap);

  const leftCapMesh = new THREE.Mesh(
    new THREE.BoxGeometry(0.34, 1.0, 0.26),
    material,
  );
  leftCapMesh.name = 'left_cap_mesh';
  leftCap.add(leftCapMesh);

  const rightCap = new THREE.Group();
  rightCap.name = 'right_cap';
  rightCap.position.set(4.75, 1.32, 0);
  rightCap.rotation.z = -Math.PI / 14;
  railGroup.add(rightCap);

  const rightCapMesh = new THREE.Mesh(
    new THREE.BoxGeometry(0.34, 1.0, 0.26),
    material,
  );
  rightCapMesh.name = 'right_cap_mesh';
  rightCap.add(rightCapMesh);

  return root;
}
