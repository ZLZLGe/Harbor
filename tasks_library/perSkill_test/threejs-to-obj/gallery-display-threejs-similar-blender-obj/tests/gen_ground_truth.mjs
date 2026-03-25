import * as THREE from 'three';
import fs from 'fs';
import { pathToFileURL } from 'url';

function isWorldVisible(object) {
  let current = object;
  while (current) {
    if (current.visible === false) {
      return false;
    }
    current = current.parent;
  }
  return true;
}

function canonicalizePoints(points) {
  const seen = new Set();
  const uniquePoints = [];

  for (const point of points) {
    const rounded = point.map((value) => Number(value.toFixed(6)));
    const key = rounded.join(',');
    if (!seen.has(key)) {
      seen.add(key);
      uniquePoints.push(rounded);
    }
  }

  uniquePoints.sort((left, right) => {
    if (left[0] !== right[0]) {
      return left[0] - right[0];
    }
    if (left[1] !== right[1]) {
      return left[1] - right[1];
    }
    return left[2] - right[2];
  });

  return uniquePoints;
}

async function main() {
  const moduleUrl = pathToFileURL('/root/data/display_scene.js').href;
  const sceneModule = await import(moduleUrl);
  const root = sceneModule.createDisplayAssembly();
  root.updateMatrixWorld(true);

  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
  const bakedMatrix = new THREE.Matrix4();
  const instanceMatrix = new THREE.Matrix4();
  const points = [];

  const collectPoints = (sourceGeometry, worldMatrix) => {
    let geometry = sourceGeometry.clone();
    geometry.applyMatrix4(worldMatrix);
    geometry.applyMatrix4(axisMatrix);
    const position = geometry.attributes.position;
    for (let index = 0; index < position.count; index += 1) {
      points.push([
        position.getX(index),
        position.getY(index),
        position.getZ(index),
      ]);
    }
  };

  root.traverse((object) => {
    if (!isWorldVisible(object)) {
      return;
    }

    if (object.isInstancedMesh) {
      for (let index = 0; index < object.count; index += 1) {
        object.getMatrixAt(index, instanceMatrix);
        bakedMatrix.copy(object.matrixWorld).multiply(instanceMatrix);
        collectPoints(object.geometry, bakedMatrix);
      }
      return;
    }

    if (object.isMesh) {
      collectPoints(object.geometry, object.matrixWorld);
    }
  });

  if (points.length === 0) {
    throw new Error('No visible points found.');
  }

  const canonicalPoints = canonicalizePoints(points);
  fs.mkdirSync('/root/ground_truth', { recursive: true });
  fs.writeFileSync(
    '/root/ground_truth/display_points.json',
    JSON.stringify({ points: canonicalPoints }, null, 2)
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
