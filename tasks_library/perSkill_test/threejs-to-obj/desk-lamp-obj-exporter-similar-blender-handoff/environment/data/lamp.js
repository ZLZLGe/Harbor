import * as THREE from 'three';

export function createLampAssembly() {
  const CM = 0.35;
  const root = new THREE.Group();
  root.name = 'desk_lamp';

  const baseGroup = new THREE.Group();
  baseGroup.name = 'base_group';
  root.add(baseGroup);

  const baseRadius = 13 * CM;
  const baseHeight = 1.8 * CM;
  const baseGeometry = new THREE.CylinderGeometry(baseRadius, baseRadius, baseHeight, 48);
  const base = new THREE.Mesh(baseGeometry, new THREE.MeshBasicMaterial());
  base.name = 'base_plate';
  base.position.y = baseHeight / 2;
  baseGroup.add(base);

  const baseRingGeometry = new THREE.TorusGeometry(baseRadius * 0.62, 0.45 * CM, 20, 48);
  const baseRing = new THREE.Mesh(baseRingGeometry, new THREE.MeshBasicMaterial());
  baseRing.name = 'base_ring';
  baseRing.rotation.x = Math.PI / 2;
  baseRing.position.y = baseHeight + 0.25 * CM;
  baseGroup.add(baseRing);

  const stemPivot = new THREE.Group();
  stemPivot.name = 'stem_pivot';
  stemPivot.position.set(0, baseHeight, 0);
  stemPivot.rotation.z = THREE.MathUtils.degToRad(-8);
  root.add(stemPivot);

  const stemGeometry = new THREE.CylinderGeometry(0.85 * CM, 1.05 * CM, 17 * CM, 32);
  const stem = new THREE.Mesh(stemGeometry, new THREE.MeshBasicMaterial());
  stem.name = 'stem';
  stem.position.y = 8.5 * CM;
  stemPivot.add(stem);

  const elbowGroup = new THREE.Group();
  elbowGroup.name = 'elbow_group';
  elbowGroup.position.set(0.2 * CM, 16.8 * CM, 0.4 * CM);
  elbowGroup.rotation.z = THREE.MathUtils.degToRad(36);
  stemPivot.add(elbowGroup);

  const lowerArmGeometry = new THREE.BoxGeometry(2.4 * CM, 11 * CM, 1.3 * CM);
  const lowerArm = new THREE.Mesh(lowerArmGeometry, new THREE.MeshBasicMaterial());
  lowerArm.name = 'lower_arm';
  lowerArm.position.y = 5.5 * CM;
  elbowGroup.add(lowerArm);

  const hingeGeometry = new THREE.CylinderGeometry(1.4 * CM, 1.4 * CM, 1.1 * CM, 24);
  const hinge = new THREE.Mesh(hingeGeometry, new THREE.MeshBasicMaterial());
  hinge.name = 'elbow_hinge';
  hinge.rotation.z = Math.PI / 2;
  hinge.position.y = 11 * CM;
  elbowGroup.add(hinge);

  const upperArmGroup = new THREE.Group();
  upperArmGroup.name = 'upper_arm_group';
  upperArmGroup.position.set(0, 11 * CM, 0);
  upperArmGroup.rotation.z = THREE.MathUtils.degToRad(-52);
  elbowGroup.add(upperArmGroup);

  const upperArmGeometry = new THREE.BoxGeometry(2.0 * CM, 12 * CM, 1.2 * CM);
  const upperArm = new THREE.Mesh(upperArmGeometry, new THREE.MeshBasicMaterial());
  upperArm.name = 'upper_arm';
  upperArm.position.y = 6 * CM;
  upperArmGroup.add(upperArm);

  const headPivot = new THREE.Group();
  headPivot.name = 'head_pivot';
  headPivot.position.set(0.1 * CM, 12 * CM, 0.2 * CM);
  headPivot.rotation.z = THREE.MathUtils.degToRad(28);
  headPivot.rotation.y = THREE.MathUtils.degToRad(10);
  upperArmGroup.add(headPivot);

  const neckGeometry = new THREE.CylinderGeometry(0.55 * CM, 0.7 * CM, 3.5 * CM, 18);
  const neck = new THREE.Mesh(neckGeometry, new THREE.MeshBasicMaterial());
  neck.name = 'neck';
  neck.position.y = 1.75 * CM;
  headPivot.add(neck);

  const shadeGroup = new THREE.Group();
  shadeGroup.name = 'shade_group';
  shadeGroup.position.y = 3.4 * CM;
  shadeGroup.rotation.x = THREE.MathUtils.degToRad(14);
  shadeGroup.scale.set(1.0, 0.92, 1.08);
  headPivot.add(shadeGroup);

  const shadeGeometry = new THREE.CylinderGeometry(4.7 * CM, 2.2 * CM, 6.2 * CM, 40, 1, true);
  const shade = new THREE.Mesh(shadeGeometry, new THREE.MeshBasicMaterial());
  shade.name = 'shade';
  shade.rotation.z = Math.PI / 2;
  shade.position.set(3.4 * CM, 0, 0);
  shadeGroup.add(shade);

  const rimGeometry = new THREE.TorusGeometry(2.25 * CM, 0.18 * CM, 12, 40);
  const rim = new THREE.Mesh(rimGeometry, new THREE.MeshBasicMaterial());
  rim.name = 'shade_rim';
  rim.rotation.y = Math.PI / 2;
  rim.position.set(6.45 * CM, 0, 0);
  shadeGroup.add(rim);

  const bulbGeometry = new THREE.SphereGeometry(1.5 * CM, 24, 16);
  const bulb = new THREE.Mesh(bulbGeometry, new THREE.MeshBasicMaterial());
  bulb.name = 'bulb';
  bulb.position.set(3.4 * CM, 0, 0);
  shadeGroup.add(bulb);

  const yokeGeometry = new THREE.TorusGeometry(1.7 * CM, 0.16 * CM, 10, 36, Math.PI);
  const yoke = new THREE.Mesh(yokeGeometry, new THREE.MeshBasicMaterial());
  yoke.name = 'shade_yoke';
  yoke.rotation.z = Math.PI / 2;
  yoke.position.set(0.2 * CM, 0, 0);
  shadeGroup.add(yoke);

  const baseScrewGeometry = new THREE.CylinderGeometry(0.32 * CM, 0.32 * CM, 0.45 * CM, 18);
  const baseScrews = new THREE.InstancedMesh(baseScrewGeometry, new THREE.MeshBasicMaterial(), 4);
  baseScrews.name = 'base_screws';
  const temp = new THREE.Object3D();
  const screwRadius = baseRadius * 0.72;
  for (let i = 0; i < 4; i += 1) {
    const angle = (i / 4) * Math.PI * 2 + Math.PI / 4;
    temp.position.set(Math.cos(angle) * screwRadius, baseHeight + 0.2 * CM, Math.sin(angle) * screwRadius);
    temp.rotation.x = 0;
    temp.rotation.y = angle * 0.25;
    temp.rotation.z = 0;
    temp.updateMatrix();
    baseScrews.setMatrixAt(i, temp.matrix);
  }
  baseScrews.instanceMatrix.needsUpdate = true;
  root.add(baseScrews);

  const headScrewGeometry = new THREE.CylinderGeometry(0.18 * CM, 0.18 * CM, 0.65 * CM, 16);
  const headScrews = new THREE.InstancedMesh(headScrewGeometry, new THREE.MeshBasicMaterial(), 2);
  headScrews.name = 'head_screws';
  const headOffset = 1.25 * CM;
  for (let i = 0; i < 2; i += 1) {
    temp.position.set(0.35 * CM, i === 0 ? headOffset : -headOffset, 0.85 * CM);
    temp.rotation.set(Math.PI / 2, 0, 0);
    temp.updateMatrix();
    headScrews.setMatrixAt(i, temp.matrix);
  }
  headScrews.instanceMatrix.needsUpdate = true;
  shadeGroup.add(headScrews);

  return root;
}
