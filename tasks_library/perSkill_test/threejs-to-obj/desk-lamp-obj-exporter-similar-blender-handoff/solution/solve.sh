#!/bin/bash
set -e

mkdir -p /root/output

cat <<'EOF' > /root/export_lamp.mjs
import * as THREE from 'three';
import fs from 'fs';
import { pathToFileURL } from 'url';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

async function main() {
  const moduleUrl = pathToFileURL('/root/data/lamp.js').href;
  const lampModule = await import(moduleUrl);
  const root = lampModule.createLampAssembly();
  root.updateMatrixWorld(true);

  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
  const instanceMatrix = new THREE.Matrix4();
  const tempMatrix = new THREE.Matrix4();
  const geometries = [];

  function addGeometry(sourceGeometry, matrix) {
    let geometry = sourceGeometry.clone();
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

  root.traverse((object) => {
    if (object.isInstancedMesh) {
      for (let i = 0; i < object.count; i += 1) {
        object.getMatrixAt(i, instanceMatrix);
        tempMatrix.copy(object.matrixWorld).multiply(instanceMatrix);
        addGeometry(object.geometry, tempMatrix);
      }
      return;
    }

    if (object instanceof THREE.Mesh) {
      addGeometry(object.geometry, object.matrixWorld);
    }
  });

  const merged = mergeGeometries(geometries, false);
  const mesh = new THREE.Mesh(merged);
  mesh.name = root.name || 'desk_lamp';

  const exporter = new OBJExporter();
  fs.writeFileSync('/root/output/lamp.obj', exporter.parse(mesh));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
EOF

node /root/export_lamp.mjs
