#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/build_transfer3_csv.mjs <<'EOF'
import fs from "fs";
import * as THREE from "three";
import { pathToFileURL } from "url";

const sceneModule = await import(pathToFileURL("/root/data/transfer3_scene.js").href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
const tempMatrix = new THREE.Matrix4();
const instanceMatrix = new THREE.Matrix4();

const namedGroups = new Map();
root.traverse((obj) => {
  if (obj.isGroup && obj.name && obj !== root) {
    namedGroups.set(obj.name, obj);
  }
});

const findParentPart = (group) => {
  let current = group.parent;
  while (current) {
    if (current.isGroup && current.name && current !== root && namedGroups.has(current.name)) {
      return current.name;
    }
    current = current.parent;
  }
  return "";
};

const addGeometry = (geometries, geometry, matrix) => {
  let baked = geometry.clone();
  baked.applyMatrix4(matrix);
  baked.applyMatrix4(axisMatrix);
  if (baked.index) {
    baked = baked.toNonIndexed();
  }
  if (!baked.attributes.normal) {
    baked.computeVertexNormals();
  }
  geometries.push(baked);
};

const collectOwnedGeometry = (part) => {
  const geometries = [];

  const visit = (obj) => {
    if (obj !== part && obj.isGroup && obj.name && namedGroups.has(obj.name)) {
      return;
    }
    if (obj.isInstancedMesh) {
      const count = obj.count ?? obj.instanceCount ?? 0;
      for (let index = 0; index < count; index += 1) {
        obj.getMatrixAt(index, instanceMatrix);
        tempMatrix.copy(obj.matrixWorld).multiply(instanceMatrix);
        addGeometry(geometries, obj.geometry, tempMatrix);
      }
    } else if (obj.isMesh) {
      addGeometry(geometries, obj.geometry, obj.matrixWorld);
    }
    for (const child of obj.children) {
      visit(child);
    }
  };

  visit(part);
  return geometries;
};

const format = (value) => value.toFixed(6);

const lines = [
  "name,parent,piece_count,vertex_count,face_count,min_x,min_y,min_z,max_x,max_y,max_z"
];

for (const name of Array.from(namedGroups.keys()).sort()) {
  const part = namedGroups.get(name);
  const geometries = collectOwnedGeometry(part);
  if (!geometries.length) {
    continue;
  }
  let vertexCount = 0;
  let faceCount = 0;
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];

  for (const geometry of geometries) {
    const position = geometry.attributes.position;
    vertexCount += position.count;
    faceCount += position.count / 3;
    for (let index = 0; index < position.count; index += 1) {
      const x = position.getX(index);
      const y = position.getY(index);
      const z = position.getZ(index);
      min[0] = Math.min(min[0], x);
      min[1] = Math.min(min[1], y);
      min[2] = Math.min(min[2], z);
      max[0] = Math.max(max[0], x);
      max[1] = Math.max(max[1], y);
      max[2] = Math.max(max[2], z);
    }
  }

  lines.push(
    [
      name,
      findParentPart(part),
      geometries.length,
      vertexCount,
      faceCount,
      format(min[0]),
      format(min[1]),
      format(min[2]),
      format(max[0]),
      format(max[1]),
      format(max[2])
    ].join(",")
  );
}

fs.writeFileSync("/root/output/geometry_audit.csv", `${lines.join("\n")}\n`);
EOF

node /root/build_transfer3_csv.mjs
