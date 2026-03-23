import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

async function main() {
  const sceneModule = await import(pathToFileURL('/root/data/object.js').href);
  const root = sceneModule.createScene();
  root.updateMatrixWorld(true);

  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
  const tempMatrix = new THREE.Matrix4();
  const instanceMatrix = new THREE.Matrix4();
  const geometries = [];

  const pushGeometry = (geometrySource, matrix) => {
    let geometry = geometrySource.clone();
    geometry.applyMatrix4(matrix);
    geometry.applyMatrix4(axisMatrix);
    if (geometry.index) {
      geometry = geometry.toNonIndexed();
    }
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }
    geometries.push(geometry);
  };

  root.traverse((node) => {
    if (node.isInstancedMesh) {
      const count = node.count ?? node.instanceCount ?? 0;
      for (let index = 0; index < count; index += 1) {
        node.getMatrixAt(index, instanceMatrix);
        tempMatrix.copy(node.matrixWorld).multiply(instanceMatrix);
        pushGeometry(node.geometry, tempMatrix);
      }
      return;
    }
    if (node instanceof THREE.Mesh) {
      pushGeometry(node.geometry, node.matrixWorld);
    }
  });

  const merged = mergeGeometries(geometries, false);
  fs.mkdirSync('/root/ground_truth', { recursive: true });
  fs.writeFileSync(
    '/root/ground_truth/safety_barrier.obj',
    new OBJExporter().parse(new THREE.Mesh(merged)),
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
