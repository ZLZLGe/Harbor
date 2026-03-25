import * as THREE from "three";

export function createScene() {
  const root = new THREE.Group();
  root.name = "loading_yard";

  const exportableLoader = new THREE.Group();
  exportableLoader.name = "exportable_loader";
  exportableLoader.userData.exportable = true;
  exportableLoader.position.set(-1.4, 0.5, 0.8);
  exportableLoader.rotation.y = Math.PI / 9;
  root.add(exportableLoader);

  const base = new THREE.Mesh(new THREE.BoxGeometry(3.0, 0.5, 1.7));
  base.position.set(0, 0.25, 0);
  exportableLoader.add(base);

  const mast = new THREE.Mesh(new THREE.BoxGeometry(0.45, 2.9, 0.45));
  mast.position.set(-0.9, 1.75, -0.25);
  exportableLoader.add(mast);

  const liftArm = new THREE.Group();
  liftArm.position.set(-0.55, 2.45, -0.25);
  liftArm.rotation.z = -Math.PI / 8;
  exportableLoader.add(liftArm);

  const boom = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.28, 0.35));
  boom.position.set(1.0, 0.0, 0.0);
  liftArm.add(boom);

  const hookGroup = new THREE.Group();
  hookGroup.position.set(2.2, -0.18, 0);
  hookGroup.rotation.z = Math.PI / 10;
  liftArm.add(hookGroup);

  const hook = new THREE.Mesh(new THREE.TorusGeometry(0.26, 0.05, 12, 32, Math.PI * 1.3));
  hook.rotation.z = Math.PI / 2;
  hookGroup.add(hook);

  const exportablePallets = new THREE.Group();
  exportablePallets.name = "exportable_pallets";
  exportablePallets.userData.exportable = true;
  exportablePallets.position.set(2.4, 0.0, -1.7);
  exportablePallets.rotation.y = -Math.PI / 7;
  root.add(exportablePallets);

  const palletBase = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.22, 1.4));
  palletBase.position.set(0, 0.11, 0);
  exportablePallets.add(palletBase);

  const crateGeometry = new THREE.BoxGeometry(0.52, 0.52, 0.52);
  const crateMaterial = new THREE.MeshBasicMaterial();
  const crates = new THREE.InstancedMesh(crateGeometry, crateMaterial, 6);
  crates.name = "crates";

  const helper = new THREE.Object3D();
  let matrixIndex = 0;
  for (let row = 0; row < 2; row += 1) {
    for (let col = 0; col < 3; col += 1) {
      helper.position.set(-0.55 + col * 0.55, 0.37 + row * 0.55, -0.32 + (row % 2) * 0.24);
      helper.rotation.y = (col - 1) * 0.08;
      helper.updateMatrix();
      crates.setMatrixAt(matrixIndex, helper.matrix);
      matrixIndex += 1;
    }
  }
  crates.instanceMatrix.needsUpdate = true;
  exportablePallets.add(crates);

  const guideFrame = new THREE.Group();
  guideFrame.name = "guide_frame";
  guideFrame.position.set(0.3, 0.0, 2.8);
  root.add(guideFrame);

  const guideBlock = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.16, 0.16));
  guideBlock.position.set(0, 1.8, 0);
  guideFrame.add(guideBlock);

  const hiddenReference = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.5, 6.0));
  hiddenReference.position.set(0, -0.25, 0);
  guideFrame.add(hiddenReference);

  return root;
}
