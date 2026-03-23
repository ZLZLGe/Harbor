import * as THREE from 'three';

export function createScene() {
  const root = new THREE.Group();
  root.name = 'info_kiosk';

  const material = new THREE.MeshBasicMaterial();

  const platform = new THREE.Mesh(
    new THREE.BoxGeometry(3.6, 0.32, 2.4),
    material,
  );
  platform.name = 'platform';
  platform.position.set(0, 0.16, 0);
  root.add(platform);

  const mast = new THREE.Mesh(
    new THREE.CylinderGeometry(0.22, 0.26, 3.2, 24),
    material,
  );
  mast.name = 'mast';
  mast.position.set(-0.9, 1.92, 0.1);
  root.add(mast);

  const screenRig = new THREE.Group();
  screenRig.name = 'screen_rig';
  screenRig.position.set(0.15, 1.42, 0);
  screenRig.rotation.y = Math.PI / 8;
  screenRig.rotation.z = -Math.PI / 16;
  root.add(screenRig);

  const screenFrame = new THREE.Mesh(
    new THREE.BoxGeometry(2.2, 1.42, 0.12),
    material,
  );
  screenFrame.name = 'screen_frame';
  screenFrame.position.set(0.35, 0.92, 0);
  screenRig.add(screenFrame);

  const screenBezel = new THREE.Mesh(
    new THREE.BoxGeometry(1.82, 1.02, 0.06),
    material,
  );
  screenBezel.name = 'screen_bezel';
  screenBezel.position.set(0.38, 0.92, 0.09);
  screenRig.add(screenBezel);

  const canopyGroup = new THREE.Group();
  canopyGroup.name = 'canopy_group';
  canopyGroup.position.set(0.08, 3.35, 0);
  canopyGroup.rotation.z = Math.PI / 22;
  canopyGroup.scale.set(1.1, 1.0, 0.95);
  root.add(canopyGroup);

  const canopy = new THREE.Mesh(
    new THREE.BoxGeometry(3.0, 0.18, 2.0),
    material,
  );
  canopy.name = 'canopy';
  canopy.position.set(0.1, 0, 0);
  canopyGroup.add(canopy);

  const badgeRig = new THREE.Group();
  badgeRig.name = 'badge_rig';
  badgeRig.position.set(1.15, 0.84, -0.92);
  badgeRig.rotation.y = -Math.PI / 6;
  badgeRig.scale.set(0.92, 1.35, -0.7);
  root.add(badgeRig);

  const badgeTilt = new THREE.Group();
  badgeTilt.name = 'badge_tilt';
  badgeTilt.rotation.x = -Math.PI / 9;
  badgeTilt.rotation.z = Math.PI / 18;
  badgeRig.add(badgeTilt);

  const badge = new THREE.Mesh(
    new THREE.BoxGeometry(0.9, 0.18, 0.55),
    material,
  );
  badge.name = 'badge';
  badge.position.set(0, 0.12, 0);
  badgeTilt.add(badge);

  const fastenerRing = new THREE.Group();
  fastenerRing.name = 'fastener_ring';
  fastenerRing.position.set(0.34, 0.92, 0.07);
  screenRig.add(fastenerRing);

  const fastenerGeometry = new THREE.CylinderGeometry(0.06, 0.06, 0.1, 14);
  const fasteners = new THREE.InstancedMesh(fastenerGeometry, material, 4);
  fasteners.name = 'fasteners';

  const offsets = [
    [-0.88, 0.52, 0],
    [0.88, 0.52, 0],
    [-0.88, -0.52, 0],
    [0.88, -0.52, 0],
  ];
  const temp = new THREE.Object3D();
  offsets.forEach(([x, y, z], index) => {
    temp.position.set(x, y, z);
    temp.rotation.x = Math.PI / 2;
    temp.updateMatrix();
    fasteners.setMatrixAt(index, temp.matrix);
  });
  fasteners.instanceMatrix.needsUpdate = true;
  fastenerRing.add(fasteners);

  return root;
}
