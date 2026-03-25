import * as THREE from 'three';

function createWing(direction) {
  const wingRoot = new THREE.Group();
  wingRoot.position.set(direction * 4.8, 0.15, -0.35);
  wingRoot.rotation.y = direction * Math.PI / 6;
  wingRoot.scale.set(direction * 1.05, 0.88, 0.72);

  const wingTilt = new THREE.Group();
  wingTilt.rotation.z = direction * Math.PI / 18;
  wingTilt.scale.set(1.18, 0.78, 0.56);
  wingRoot.add(wingTilt);

  const panel = new THREE.Mesh(new THREE.BoxGeometry(1.9, 2.7, 0.18));
  panel.name = `wing_panel_${direction > 0 ? 'right' : 'left'}`;
  panel.position.set(0, 0.25, -0.08);
  wingTilt.add(panel);

  const rib = new THREE.Mesh(new THREE.BoxGeometry(0.22, 2.9, 0.34));
  rib.name = `wing_rib_${direction > 0 ? 'right' : 'left'}`;
  rib.position.set(0.72, 0.08, 0.06);
  wingTilt.add(rib);

  return wingRoot;
}

export function createDisplayAssembly() {
  const root = new THREE.Group();
  root.name = 'gallery_display';

  const baseAssembly = new THREE.Group();
  baseAssembly.name = 'base_assembly';
  root.add(baseAssembly);

  const pedestal = new THREE.Mesh(new THREE.BoxGeometry(14.0, 1.2, 10.0));
  pedestal.name = 'pedestal';
  pedestal.position.set(0, 0.6, 0);
  baseAssembly.add(pedestal);

  const topDeck = new THREE.Mesh(new THREE.BoxGeometry(11.8, 0.35, 7.9));
  topDeck.name = 'top_deck';
  topDeck.position.set(0, 1.37, 0);
  baseAssembly.add(topDeck);

  const frontApron = new THREE.Mesh(new THREE.BoxGeometry(10.4, 1.0, 0.55));
  frontApron.name = 'front_apron';
  frontApron.position.set(0, 1.05, 5.02);
  baseAssembly.add(frontApron);

  const towerAssembly = new THREE.Group();
  towerAssembly.name = 'tower_assembly';
  towerAssembly.position.set(0, 1.55, 0);
  root.add(towerAssembly);

  const leftPost = new THREE.Mesh(new THREE.BoxGeometry(0.7, 8.5, 0.9));
  leftPost.name = 'left_post';
  leftPost.position.set(-5.15, 4.25, 0);
  towerAssembly.add(leftPost);

  const rightPost = new THREE.Mesh(new THREE.BoxGeometry(0.7, 8.5, 0.9));
  rightPost.name = 'right_post';
  rightPost.position.set(5.15, 4.25, 0);
  towerAssembly.add(rightPost);

  const header = new THREE.Mesh(new THREE.BoxGeometry(11.2, 0.9, 1.0));
  header.name = 'header';
  header.position.set(0, 8.95, 0);
  towerAssembly.add(header);

  const signAssembly = new THREE.Group();
  signAssembly.name = 'sign_assembly';
  signAssembly.position.set(0, 8.95, 0.1);
  towerAssembly.add(signAssembly);

  const signFrame = new THREE.Group();
  signFrame.name = 'sign_frame';
  signFrame.position.set(0, -0.15, -0.45);
  signFrame.rotation.x = -Math.PI / 18;
  signFrame.rotation.z = Math.PI / 36;
  signAssembly.add(signFrame);

  const signPanel = new THREE.Mesh(new THREE.BoxGeometry(7.4, 2.3, 0.22));
  signPanel.name = 'sign_panel';
  signPanel.position.set(0, 0.1, 0);
  signFrame.add(signPanel);

  const signBrace = new THREE.Mesh(new THREE.BoxGeometry(7.8, 0.28, 0.55));
  signBrace.name = 'sign_brace';
  signBrace.position.set(0, -1.2, -0.12);
  signFrame.add(signBrace);

  signFrame.add(createWing(-1));
  signFrame.add(createWing(1));

  const artworkCarrier = new THREE.Group();
  artworkCarrier.name = 'artwork_carrier';
  artworkCarrier.position.set(0, 4.15, -0.95);
  artworkCarrier.rotation.x = -Math.PI / 10;
  artworkCarrier.rotation.z = -Math.PI / 40;
  towerAssembly.add(artworkCarrier);

  const frame = new THREE.Mesh(new THREE.BoxGeometry(6.7, 3.9, 0.32));
  frame.name = 'frame';
  artworkCarrier.add(frame);

  const canvas = new THREE.Mesh(new THREE.BoxGeometry(6.05, 3.25, 0.08));
  canvas.name = 'canvas';
  canvas.position.set(0, 0, 0.2);
  artworkCarrier.add(canvas);

  const shelf = new THREE.Mesh(new THREE.BoxGeometry(4.3, 0.24, 1.45));
  shelf.name = 'shelf';
  shelf.position.set(0, -2.35, 0.62);
  shelf.rotation.x = Math.PI / 18;
  artworkCarrier.add(shelf);

  const spotlightArm = new THREE.Group();
  spotlightArm.name = 'spotlight_arm';
  spotlightArm.position.set(0, 7.4, 0.55);
  spotlightArm.rotation.z = Math.PI / 14;
  root.add(spotlightArm);

  const armBar = new THREE.Mesh(new THREE.BoxGeometry(4.0, 0.22, 0.22));
  armBar.name = 'arm_bar';
  armBar.position.set(1.95, 0, 0);
  spotlightArm.add(armBar);

  const lampMount = new THREE.Group();
  lampMount.name = 'lamp_mount';
  lampMount.position.set(3.9, -0.18, -0.4);
  lampMount.rotation.x = Math.PI / 5;
  lampMount.rotation.y = -Math.PI / 8;
  spotlightArm.add(lampMount);

  const lampBody = new THREE.Mesh(new THREE.CylinderGeometry(0.48, 0.34, 1.15, 24));
  lampBody.name = 'lamp_body';
  lampBody.rotation.z = Math.PI / 2;
  lampMount.add(lampBody);

  const lampBezel = new THREE.Mesh(new THREE.CylinderGeometry(0.56, 0.56, 0.16, 24));
  lampBezel.name = 'lamp_bezel';
  lampBezel.position.set(0.56, 0, 0);
  lampBezel.rotation.z = Math.PI / 2;
  lampMount.add(lampBezel);

  const fastenerRig = new THREE.Group();
  fastenerRig.name = 'fastener_rig';
  fastenerRig.position.set(0, 4.15, -0.8);
  fastenerRig.rotation.x = -Math.PI / 10;
  fastenerRig.rotation.z = -Math.PI / 40;
  root.add(fastenerRig);

  const boltGeometry = new THREE.CylinderGeometry(0.11, 0.11, 0.22, 16);
  const boltMesh = new THREE.InstancedMesh(
    boltGeometry,
    new THREE.MeshBasicMaterial(),
    8
  );
  boltMesh.name = 'frame_fasteners';

  const temp = new THREE.Object3D();
  const boltPositions = [
    [-3.05, 1.6, 0.23],
    [3.05, 1.6, 0.23],
    [-3.05, -1.6, 0.23],
    [3.05, -1.6, 0.23],
    [-1.95, -2.33, 0.92],
    [1.95, -2.33, 0.92],
    [-4.55, 3.55, -0.12],
    [4.55, 3.55, -0.12],
  ];

  boltPositions.forEach((position, index) => {
    temp.position.set(position[0], position[1], position[2]);
    temp.rotation.x = Math.PI / 2;
    temp.rotation.y = index >= 6 ? Math.PI / 2 : 0;
    temp.updateMatrix();
    boltMesh.setMatrixAt(index, temp.matrix);
  });
  boltMesh.instanceMatrix.needsUpdate = true;
  fastenerRig.add(boltMesh);

  const hiddenCalibration = new THREE.Group();
  hiddenCalibration.name = 'hidden_calibration';
  hiddenCalibration.visible = false;
  hiddenCalibration.position.set(0, 6.2, -13.0);
  root.add(hiddenCalibration);

  const hiddenPlate = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.5, 3.2));
  hiddenPlate.name = 'hidden_plate';
  hiddenCalibration.add(hiddenPlate);

  const hiddenMarker = new THREE.Mesh(new THREE.ConeGeometry(0.6, 1.4, 12));
  hiddenMarker.name = 'hidden_marker';
  hiddenMarker.position.set(1.4, 0.9, -0.7);
  hiddenCalibration.add(hiddenMarker);

  return root;
}
