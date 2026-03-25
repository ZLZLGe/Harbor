import * as THREE from 'three';

function makePanelShape() {
  const shape = new THREE.Shape();
  shape.moveTo(-1.8, -0.55);
  shape.lineTo(0.68, -0.55);
  shape.quadraticCurveTo(0.95, -0.55, 1.12, -0.38);
  shape.lineTo(1.58, 0);
  shape.lineTo(1.12, 0.38);
  shape.quadraticCurveTo(0.95, 0.55, 0.68, 0.55);
  shape.lineTo(-1.8, 0.55);
  shape.quadraticCurveTo(-2.05, 0.55, -2.05, 0.3);
  shape.lineTo(-2.05, -0.3);
  shape.quadraticCurveTo(-2.05, -0.55, -1.8, -0.55);

  const holeCenters = [
    [-1.35, 0.22],
    [-0.72, 0.22],
    [-1.35, -0.22],
    [-0.72, -0.22],
  ];

  for (const [x, y] of holeCenters) {
    const hole = new THREE.Path();
    hole.absellipse(x, y, 0.09, 0.09, 0, Math.PI * 2, false, 0);
    shape.holes.push(hole);
  }

  return shape;
}

function makeFinialGeometry() {
  const profile = [
    new THREE.Vector2(0.0, 0.0),
    new THREE.Vector2(0.09, 0.0),
    new THREE.Vector2(0.11, 0.04),
    new THREE.Vector2(0.07, 0.09),
    new THREE.Vector2(0.13, 0.15),
    new THREE.Vector2(0.06, 0.21),
    new THREE.Vector2(0.0, 0.26),
  ];
  return new THREE.LatheGeometry(profile, 36);
}

export function buildWayfindingSignScene() {
  const root = new THREE.Group();
  root.name = 'concourse_wayfinding_sign';

  const panelThickness = 0.18;
  const holeCenters = [
    [-1.35, 0.22],
    [-0.72, 0.22],
    [-1.35, -0.22],
    [-0.72, -0.22],
  ];

  const panelGeometry = new THREE.ExtrudeGeometry(makePanelShape(), {
    depth: panelThickness,
    bevelEnabled: false,
    curveSegments: 32,
    steps: 1,
  });
  panelGeometry.translate(0, 0, -panelThickness / 2);

  const panelBlank = new THREE.Mesh(panelGeometry, new THREE.MeshStandardMaterial());
  panelBlank.name = 'panel_blank';
  panelBlank.position.set(0, 1.55, 0);
  panelBlank.userData.mountingHoleCenters = holeCenters;
  panelBlank.userData.mountingHoleRadius = 0.09;
  panelBlank.userData.panelThickness = panelThickness;
  root.add(panelBlank);

  const backStrap = new THREE.Mesh(
    new THREE.BoxGeometry(0.28, 1.15, 0.08),
    new THREE.MeshStandardMaterial(),
  );
  backStrap.name = 'back_strap';
  backStrap.position.set(-1.03, 1.4, -0.13);
  root.add(backStrap);

  const postGeometry = new THREE.BoxGeometry(0.14, 2.1, 0.14);

  const leftPost = new THREE.Mesh(postGeometry, new THREE.MeshStandardMaterial());
  leftPost.name = 'left_post';
  leftPost.position.set(-1.35, 0.95, -0.22);
  root.add(leftPost);

  const rightPost = new THREE.Mesh(postGeometry.clone(), new THREE.MeshStandardMaterial());
  rightPost.name = 'right_post';
  rightPost.position.set(-0.72, 0.95, -0.22);
  root.add(rightPost);

  const leftFinial = new THREE.Mesh(makeFinialGeometry(), new THREE.MeshStandardMaterial());
  leftFinial.name = 'left_finial';
  leftFinial.position.set(-1.35, 2.0, -0.22);
  root.add(leftFinial);

  const rightFinial = new THREE.Mesh(makeFinialGeometry(), new THREE.MeshStandardMaterial());
  rightFinial.name = 'right_finial';
  rightFinial.position.set(-0.72, 2.0, -0.22);
  root.add(rightFinial);

  return root;
}
