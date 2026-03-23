import * as THREE from 'three';

export function createScene() {
  const root = new THREE.Group();
  root.name = 'light_canopy';

  const material = new THREE.MeshBasicMaterial();

  const mast = new THREE.Mesh(
    new THREE.CylinderGeometry(0.22, 0.28, 4.2, 24),
    material,
  );
  mast.name = 'mast';
  mast.position.set(0, 2.1, 0);
  root.add(mast);

  const canopy = new THREE.Group();
  canopy.name = 'canopy';
  canopy.position.set(0, 4.25, 0);
  canopy.rotation.y = Math.PI / 12;
  root.add(canopy);

  const hub = new THREE.Mesh(
    new THREE.CylinderGeometry(0.62, 0.75, 0.36, 32),
    material,
  );
  hub.name = 'hub';
  canopy.add(hub);

  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(3.15, 0.14, 20, 72),
    material,
  );
  ring.name = 'ring';
  ring.rotation.x = Math.PI / 2;
  ring.scale.set(1.0, 1.0, 0.94);
  canopy.add(ring);

  const armGeometry = new THREE.BoxGeometry(0.26, 0.14, 3.1);
  const arms = new THREE.InstancedMesh(armGeometry, material, 6);
  arms.name = 'arms';

  const temp = new THREE.Object3D();
  for (let index = 0; index < 6; index += 1) {
    const angle = (index / 6) * Math.PI * 2;
    temp.position.set(0, 0, 0);
    temp.rotation.y = angle;
    temp.updateMatrix();
    arms.setMatrixAt(index, temp.matrix);
  }
  arms.instanceMatrix.needsUpdate = true;
  canopy.add(arms);

  const cellGeometry = new THREE.BoxGeometry(0.82, 0.12, 0.48);
  const cells = new THREE.InstancedMesh(cellGeometry, material, 12);
  cells.name = 'cells';
  for (let index = 0; index < 12; index += 1) {
    const angle = (index / 12) * Math.PI * 2;
    temp.position.set(Math.cos(angle) * 3.1, -0.18, Math.sin(angle) * 3.1);
    temp.rotation.y = angle + Math.PI / 2;
    temp.updateMatrix();
    cells.setMatrixAt(index, temp.matrix);
  }
  cells.instanceMatrix.needsUpdate = true;
  canopy.add(cells);

  const strutGeometry = new THREE.CylinderGeometry(0.06, 0.06, 2.0, 14);
  const struts = new THREE.InstancedMesh(strutGeometry, material, 3);
  struts.name = 'struts';
  const strutAngles = [0, (2 * Math.PI) / 3, (4 * Math.PI) / 3];
  strutAngles.forEach((angle, index) => {
    temp.position.set(Math.cos(angle) * 1.2, -0.8, Math.sin(angle) * 1.2);
    temp.rotation.z = Math.PI / 7;
    temp.rotation.y = angle;
    temp.updateMatrix();
    struts.setMatrixAt(index, temp.matrix);
  });
  struts.instanceMatrix.needsUpdate = true;
  canopy.add(struts);

  const bannerRig = new THREE.Group();
  bannerRig.name = 'banner_rig';
  bannerRig.position.set(1.85, -0.34, -1.18);
  bannerRig.rotation.y = -Math.PI / 8;
  bannerRig.scale.set(1.0, 0.72, -0.82);
  canopy.add(bannerRig);

  const banner = new THREE.Mesh(
    new THREE.BoxGeometry(1.1, 0.2, 0.68),
    material,
  );
  banner.name = 'banner';
  bannerRig.add(banner);

  return root;
}
