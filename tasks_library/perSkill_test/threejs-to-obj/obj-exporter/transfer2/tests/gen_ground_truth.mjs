import * as THREE from "three";
import fs from "fs";
import { pathToFileURL } from "url";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { OBJExporter } from "three/examples/jsm/exporters/OBJExporter.js";

function hasExportableAncestor(node) {
  let current = node;
  while (current) {
    if (current.userData?.exportable === true) {
      return true;
    }
    current = current.parent;
  }
  return false;
}

async function main() {
  const sceneModule = await import(pathToFileURL("/root/data/loading_yard.js").href);
  const root = sceneModule.createScene();
  root.updateMatrixWorld(true);

  const geometries = [];
  const instanceMatrix = new THREE.Matrix4();
  const combinedMatrix = new THREE.Matrix4();
  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);

  function addGeometry(source, matrix) {
    let geometry = source.clone();
    geometry.applyMatrix4(matrix);
    geometry.applyMatrix4(axisMatrix);
    if (geometry.index) {
      geometry = geometry.toNonIndexed();
    }
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }
    geometries.push(geometry);
  }

  root.traverse((node) => {
    if (!hasExportableAncestor(node)) {
      return;
    }
    if (node.isInstancedMesh) {
      const count = node.count ?? node.instanceCount ?? 0;
      for (let index = 0; index < count; index += 1) {
        node.getMatrixAt(index, instanceMatrix);
        combinedMatrix.copy(node.matrixWorld).multiply(instanceMatrix);
        addGeometry(node.geometry, combinedMatrix);
      }
      return;
    }
    if (node instanceof THREE.Mesh) {
      addGeometry(node.geometry, node.matrixWorld);
    }
  });

  fs.mkdirSync("/root/ground_truth", { recursive: true });
  const merged = mergeGeometries(geometries, false);
  const exporter = new OBJExporter();
  fs.writeFileSync("/root/ground_truth/loading_yard.obj", exporter.parse(new THREE.Mesh(merged)));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
