#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/export_similar.js <<'EOF'
import * as THREE from "three";
import fs from "fs";
import { pathToFileURL } from "url";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { OBJExporter } from "three/examples/jsm/exporters/OBJExporter.js";

async function main() {
  const sceneModule = await import(pathToFileURL("/root/data/pedestal_showpiece.js").href);
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

  const merged = mergeGeometries(geometries, false);
  const exporter = new OBJExporter();
  const mesh = new THREE.Mesh(merged);
  fs.writeFileSync("/root/output/pedestal_showpiece.obj", exporter.parse(mesh));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
EOF

node /root/export_similar.js
