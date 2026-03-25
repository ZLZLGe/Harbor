#!/bin/bash
set -eu

mkdir -p /root/output /root/output/floors

node --input-type=module <<'EOF'
import fs from 'fs';
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { pathToFileURL } from 'url';

const sceneModule = await import(pathToFileURL('/root/data/atrium_scene.js').href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

const exporter = new OBJExporter();
const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
const floorMap = new Map();

root.traverse((object) => {
  if (object.isGroup && object.name) {
    floorMap.set(object.name, object);
  }
});

function findParentFloor(floorObject) {
  let parent = floorObject.parent;
  while (parent) {
    if (parent.isGroup && parent.name && floorMap.has(parent.name)) {
      return parent.name;
    }
    parent = parent.parent;
  }
  return null;
}

function collectOwnedMeshes(floorObject) {
  const meshes = [];

  const visit = (object) => {
    if (object !== floorObject && object.isGroup && object.name && floorMap.has(object.name)) {
      return;
    }
    if (object.isMesh) {
      meshes.push(object);
    }
    for (const child of object.children) {
      visit(child);
    }
  };

  visit(floorObject);
  return meshes;
}

function bakeGeometry(mesh) {
  let geometry = mesh.geometry.clone();
  geometry.applyMatrix4(mesh.matrixWorld);
  geometry.applyMatrix4(axisMatrix);
  if (geometry.index) {
    geometry = geometry.toNonIndexed();
  }
  if (!geometry.attributes.normal) {
    geometry.computeVertexNormals();
  }
  return geometry;
}

const manifest = {
  scene_file: 'atrium_scene.js',
  axis_conversion: 'Y-up to Z-up',
  floors: [],
};

for (const floorName of Array.from(floorMap.keys()).sort()) {
  const floorObject = floorMap.get(floorName);
  const ownedMeshes = collectOwnedMeshes(floorObject);
  if (ownedMeshes.length === 0) {
    continue;
  }

  const merged = mergeGeometries(ownedMeshes.map(bakeGeometry), false);
  const outputFile = `floors/${floorName}.obj`;
  const outputPath = `/root/output/${outputFile}`;

  fs.writeFileSync(outputPath, exporter.parse(new THREE.Mesh(merged)));
  manifest.floors.push({
    floor_name: floorName,
    parent_floor: findParentFloor(floorObject),
    mesh_count: ownedMeshes.length,
    merged_obj_file: outputFile,
  });
}

fs.writeFileSync(
  '/root/output/floor_manifest.json',
  `${JSON.stringify(manifest, null, 2)}\n`
);
EOF
