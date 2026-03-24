import * as THREE from 'three';

const cell = {
  x: 3.8,
  y: 4.6,
  z: 5.2,
};

const repeats = {
  x: 2,
  y: 2,
  z: 1,
};

const atomRadii = {
  metal: 0.42,
  oxygen: 0.23,
};

const metalBasis = [
  [0.22, 0.24, 0.28],
  [0.72, 0.68, 0.54],
];

const oxygenBasis = [
  [0.38, 0.36, 0.18],
  [0.12, 0.44, 0.46],
  [0.58, 0.54, 0.72],
  [0.84, 0.82, 0.42],
];

const bondLinks = [
  { metal: 0, oxygen: 0 },
  { metal: 0, oxygen: 1 },
  { metal: 1, oxygen: 2 },
  { metal: 1, oxygen: 3 },
  { metal: 0, oxygen: 2 },
  { metal: 1, oxygen: 1 },
];

function latticePosition(ix, iy, iz, fractional) {
  return new THREE.Vector3(
    (ix + fractional[0]) * cell.x,
    (iy + fractional[1]) * cell.y,
    (iz + fractional[2]) * cell.z,
  );
}

function createBond(start, end, radius, name) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();
  const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
  const geometry = new THREE.CylinderGeometry(radius, radius, length, 18);
  const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial());
  mesh.name = name;
  mesh.position.copy(midpoint);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  return mesh;
}

function populateInstancedAtoms(target, basis, radius) {
  const temp = new THREE.Object3D();
  let index = 0;

  for (let ix = 0; ix < repeats.x; ix += 1) {
    for (let iy = 0; iy < repeats.y; iy += 1) {
      for (let iz = 0; iz < repeats.z; iz += 1) {
        for (const fractional of basis) {
          const position = latticePosition(ix, iy, iz, fractional);
          temp.position.copy(position);
          temp.rotation.set(0, 0, 0);
          temp.scale.setScalar(1);
          temp.updateMatrix();
          target.setMatrixAt(index, temp.matrix);
          index += 1;
        }
      }
    }
  }

  target.instanceMatrix.needsUpdate = true;
  target.userData.atomRadius = radius;
}

export function createMolecularLatticeScene() {
  const root = new THREE.Group();
  root.name = 'molecular_lattice';

  const scanStage = new THREE.Group();
  scanStage.name = 'scan_stage';
  scanStage.position.set(-2.1, 0.95, 1.4);
  scanStage.rotation.set(
    THREE.MathUtils.degToRad(-11),
    THREE.MathUtils.degToRad(24),
    THREE.MathUtils.degToRad(7),
  );
  root.add(scanStage);

  const crystalFrame = new THREE.Group();
  crystalFrame.name = 'crystal_frame';
  crystalFrame.position.set(0.35, 0.2, -0.45);
  scanStage.add(crystalFrame);

  const guidePlate = new THREE.Mesh(
    new THREE.BoxGeometry((cell.x * repeats.x) + 0.8, 0.18, (cell.z * repeats.z) + 1.0),
    new THREE.MeshBasicMaterial(),
  );
  guidePlate.name = 'guide_plate';
  guidePlate.position.set(
    (cell.x * repeats.x) / 2,
    -0.09,
    (cell.z * repeats.z) / 2,
  );
  crystalFrame.add(guidePlate);

  const metalAtoms = new THREE.InstancedMesh(
    new THREE.SphereGeometry(atomRadii.metal, 20, 14),
    new THREE.MeshBasicMaterial(),
    repeats.x * repeats.y * repeats.z * metalBasis.length,
  );
  metalAtoms.name = 'metal_atoms';
  populateInstancedAtoms(metalAtoms, metalBasis, atomRadii.metal);
  crystalFrame.add(metalAtoms);

  const oxygenAtoms = new THREE.InstancedMesh(
    new THREE.SphereGeometry(atomRadii.oxygen, 18, 12),
    new THREE.MeshBasicMaterial(),
    repeats.x * repeats.y * repeats.z * oxygenBasis.length,
  );
  oxygenAtoms.name = 'oxygen_atoms';
  populateInstancedAtoms(oxygenAtoms, oxygenBasis, atomRadii.oxygen);
  crystalFrame.add(oxygenAtoms);

  for (let ix = 0; ix < repeats.x; ix += 1) {
    for (let iy = 0; iy < repeats.y; iy += 1) {
      for (let iz = 0; iz < repeats.z; iz += 1) {
        const motif = new THREE.Group();
        motif.name = `motif_${ix}_${iy}_${iz}`;
        crystalFrame.add(motif);

        const metalPositions = metalBasis.map((fractional) => latticePosition(ix, iy, iz, fractional));
        const oxygenPositions = oxygenBasis.map((fractional) => latticePosition(ix, iy, iz, fractional));

        bondLinks.forEach((link, bondIndex) => {
          const bond = createBond(
            metalPositions[link.metal],
            oxygenPositions[link.oxygen],
            0.08,
            `bond_${ix}_${iy}_${iz}_${bondIndex}`,
          );
          motif.add(bond);
        });

        if (ix + 1 < repeats.x) {
          const bridge = createBond(
            metalPositions[1],
            latticePosition(ix + 1, iy, iz, oxygenBasis[0]),
            0.06,
            `bridge_x_${ix}_${iy}_${iz}`,
          );
          motif.add(bridge);
        }

        if (iy + 1 < repeats.y) {
          const bridge = createBond(
            metalPositions[0],
            latticePosition(ix, iy + 1, iz, oxygenBasis[3]),
            0.06,
            `bridge_y_${ix}_${iy}_${iz}`,
          );
          motif.add(bridge);
        }
      }
    }
  }

  return root;
}
