#!/bin/bash
set -euo pipefail

mkdir -p /root/output/links

cat > /root/export_similar.mjs <<'EOF'
import fs from "fs";
import path from "path";
import * as THREE from "three";
import { OBJExporter } from "three/examples/jsm/exporters/OBJExporter.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { pathToFileURL } from "url";

const sceneModule = await import(pathToFileURL("/root/data/similar_scene.js").href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
const tempMatrix = new THREE.Matrix4();
const instanceMatrix = new THREE.Matrix4();
const exporter = new OBJExporter();

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
  return null;
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

const countObj = (text) => {
  let vertexCount = 0;
  let faceCount = 0;
  for (const line of text.split("\n")) {
    if (line.startsWith("v ")) {
      vertexCount += 1;
    } else if (line.startsWith("f ")) {
      faceCount += 1;
    }
  }
  return { vertexCount, faceCount };
};

const partEntries = [];
for (const name of Array.from(namedGroups.keys()).sort()) {
  const part = namedGroups.get(name);
  const geometries = collectOwnedGeometry(part);
  if (!geometries.length) {
    continue;
  }
  const merged = mergeGeometries(geometries, false);
  const mesh = new THREE.Mesh(merged);
  const objText = exporter.parse(mesh);
  const outPath = path.join("/root/output/links", `${name}.obj`);
  fs.writeFileSync(outPath, objText);
  const counts = countObj(objText);
  partEntries.push({
    name,
    parent: findParentPart(part),
    obj_file: `links/${name}.obj`,
    vertex_count: counts.vertexCount,
    face_count: counts.faceCount
  });
}

fs.writeFileSync(
  "/root/output/link_manifest.json",
  JSON.stringify(
    {
      scene_name: root.name || "scene",
      parts: partEntries
    },
    null,
    2
  ) + "\n"
);
EOF

node /root/export_similar.mjs
