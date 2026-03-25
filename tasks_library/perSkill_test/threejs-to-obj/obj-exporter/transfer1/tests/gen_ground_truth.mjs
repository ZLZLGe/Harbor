import * as THREE from "three";
import fs from "fs";
import { pathToFileURL } from "url";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { OBJExporter } from "three/examples/jsm/exporters/OBJExporter.js";

async function main() {
  const sceneModule = await import(pathToFileURL("/root/data/inspection_line.js").href);
  const root = sceneModule.createScene();
  root.updateMatrixWorld(true);

  const target = root.getObjectByName("inspection_fixture");
  if (!target) {
    throw new Error("inspection_fixture not found");
  }

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

  target.traverse((node) => {
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
  fs.writeFileSync("/root/ground_truth/inspection_fixture.obj", exporter.parse(new THREE.Mesh(merged)));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
