#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/export_wayfinding_obj.mjs <<'EOF'
import fs from 'fs';
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { pathToFileURL } from 'url';

const moduleUrl = pathToFileURL('/root/data/wayfinding_scene.js').href;
const sceneModule = await import(moduleUrl);
const root = sceneModule.buildWayfindingSignScene();
root.updateMatrixWorld(true);

const zUpMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
const exportRoot = new THREE.Group();

root.traverse((obj) => {
  if (!obj.isMesh) {
    return;
  }

  const bakedGeometry = obj.geometry.clone();
  bakedGeometry.applyMatrix4(obj.matrixWorld);
  bakedGeometry.applyMatrix4(zUpMatrix);

  if (!bakedGeometry.getAttribute('normal')) {
    bakedGeometry.computeVertexNormals();
  }

  const bakedMesh = new THREE.Mesh(bakedGeometry, new THREE.MeshBasicMaterial());
  bakedMesh.name = obj.name || 'mesh';
  exportRoot.add(bakedMesh);
});

const exporter = new OBJExporter();
const objText = exporter.parse(exportRoot);
fs.writeFileSync('/root/output/wayfinding_sign.obj', objText, 'utf8');
EOF

node /root/export_wayfinding_obj.mjs
