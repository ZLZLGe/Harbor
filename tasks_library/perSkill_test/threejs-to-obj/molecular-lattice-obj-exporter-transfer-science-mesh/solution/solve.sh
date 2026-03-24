#!/bin/bash
set -e

mkdir -p /root/output

cat > /root/export_lattice.js <<'EOF'
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import fs from 'fs';
import { pathToFileURL } from 'url';

async function main() {
  const moduleUrl = pathToFileURL('/root/data/lattice.js').href;
  const sceneModule = await import(moduleUrl);
  const root = sceneModule.createMolecularLatticeScene();
  root.updateMatrixWorld(true);

  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
  const worldMatrix = new THREE.Matrix4();
  const instanceMatrix = new THREE.Matrix4();
  const geometries = [];

  const addGeometry = (sourceGeometry, matrix) => {
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
  };

  root.traverse((object) => {
    if (object.isInstancedMesh) {
      const count = object.count ?? object.instanceCount ?? 0;
      for (let index = 0; index < count; index += 1) {
        object.getMatrixAt(index, instanceMatrix);
        worldMatrix.copy(object.matrixWorld).multiply(instanceMatrix);
        addGeometry(object.geometry, worldMatrix);
      }
      return;
    }

    if (object instanceof THREE.Mesh) {
      addGeometry(object.geometry, object.matrixWorld);
    }
  });

  const mergedGeometry = mergeGeometries(geometries, false);
  const mergedMesh = new THREE.Mesh(mergedGeometry);
  mergedMesh.name = root.name || 'lattice';

  const exporter = new OBJExporter();
  fs.writeFileSync('/root/output/lattice.obj', exporter.parse(mergedMesh));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
EOF

node /root/export_lattice.js
