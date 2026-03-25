#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/export_display.mjs <<'EOF'
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
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

async function main() {
  const moduleUrl = pathToFileURL('/root/data/display_scene.js').href;
  const sceneModule = await import(moduleUrl);
  const root = sceneModule.createDisplayAssembly();
  root.updateMatrixWorld(true);

  const geometries = [];
  const bakedMatrix = new THREE.Matrix4();
  const instanceMatrix = new THREE.Matrix4();
  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);

  const addGeometry = (sourceGeometry, worldMatrix) => {
    let geometry = sourceGeometry.clone();
    geometry.applyMatrix4(worldMatrix);
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
    if (!isWorldVisible(object)) {
      return;
    }

    if (object.isInstancedMesh) {
      for (let index = 0; index < object.count; index += 1) {
        object.getMatrixAt(index, instanceMatrix);
        bakedMatrix.copy(object.matrixWorld).multiply(instanceMatrix);
        addGeometry(object.geometry, bakedMatrix);
      }
      return;
    }

    if (object.isMesh) {
      addGeometry(object.geometry, object.matrixWorld);
    }
  });

  if (geometries.length === 0) {
    throw new Error('No visible geometry found to export.');
  }

  const mergedGeometry = mergeGeometries(geometries, false);
  const mergedMesh = new THREE.Mesh(mergedGeometry);
  mergedMesh.name = 'gallery_display';

  const exporter = new OBJExporter();
  fs.writeFileSync('/root/output/display.obj', exporter.parse(mergedMesh));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
EOF

node /root/export_display.mjs
