#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/export_scene.mjs <<'EOF'
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const SOURCE_SCENE = '/root/data/object.js';
const OUTPUT_OBJ = '/root/output/light_canopy.obj';

async function main() {
  const sceneModule = await import(pathToFileURL(SOURCE_SCENE).href);
  const root = sceneModule.createScene();
  root.updateMatrixWorld(true);

  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
  const combined = [];
  const tempMatrix = new THREE.Matrix4();
  const instanceMatrix = new THREE.Matrix4();

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
    combined.push(geometry);
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

  if (combined.length === 0) {
    throw new Error('No mesh geometry found in source scene');
  }

  const merged = mergeGeometries(combined, false);
  const exported = new OBJExporter().parse(new THREE.Mesh(merged));
  fs.writeFileSync(OUTPUT_OBJ, exported);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
EOF

node /root/export_scene.mjs
