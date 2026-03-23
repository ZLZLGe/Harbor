#!/bin/bash
set -euo pipefail

mkdir -p /root/output/leaves

cat > /root/build_transfer3.js <<'EOF'
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import fs from 'fs';
import { pathToFileURL } from 'url';

function buildPartEntries(root) {
  const parts = new Map();

  root.traverse((obj) => {
    if (obj.isGroup && obj.name) {
      parts.set(obj.name, { group: obj, meshes: [] });
    }
  });

  root.traverse((obj) => {
    if (!(obj instanceof THREE.Mesh)) {
      return;
    }
    let parent = obj.parent;
    while (parent && !(parent.isGroup && parent.name)) {
      parent = parent.parent;
    }
    if (parent && parts.has(parent.name)) {
      parts.get(parent.name).meshes.push(obj);
    }
  });

  return parts;
}

function parentPartName(group) {
  let parent = group.parent;
  while (parent && !(parent.isGroup && parent.name)) {
    parent = parent.parent;
  }
  return parent?.name ?? null;
}

function leafEntries(parts) {
  return Array.from(parts.values())
    .filter((entry) => entry.meshes.length > 0)
    .filter((entry) => {
      for (const candidate of parts.values()) {
        if (candidate.group === entry.group) {
          continue;
        }
        if (parentPartName(candidate.group) === entry.group.name) {
          return false;
        }
      }
      return true;
    })
    .sort((a, b) => a.group.name.localeCompare(b.group.name));
}

function ancestorChain(parts, group) {
  const chain = [];
  let current = group;
  while (current && current.name) {
    chain.unshift(current.name);
    const parent = parentPartName(current);
    current = parent ? parts.get(parent).group : null;
  }
  return chain;
}

function exportPartObj(meshes, outputPath) {
  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
  const geometries = [];

  for (const mesh of meshes) {
    let geometry = mesh.geometry.clone();
    geometry.applyMatrix4(mesh.matrixWorld);
    geometry.applyMatrix4(axisMatrix);
    if (geometry.index) {
      geometry = geometry.toNonIndexed();
    }
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }
    geometries.push(geometry);
  }

  const merged = mergeGeometries(geometries, false);
  fs.writeFileSync(outputPath, new OBJExporter().parse(new THREE.Mesh(merged)));
}

async function main() {
  const sceneModule = await import(pathToFileURL('/root/data/service_cart.js').href);
  const root = sceneModule.createScene();
  root.updateMatrixWorld(true);

  const parts = buildPartEntries(root);
  const leaves = leafEntries(parts);
  const index = {
    leaf_part_count: leaves.length,
    total_leaf_meshes: leaves.reduce((total, entry) => total + entry.meshes.length, 0),
    leaf_parts: [],
  };

  for (const entry of leaves) {
    const outputPath = `/root/output/leaves/${entry.group.name}.obj`;
    exportPartObj(entry.meshes, outputPath);
    index.leaf_parts.push({
      part_name: entry.group.name,
      ancestor_chain: ancestorChain(parts, entry.group),
      obj_path: outputPath,
    });
  }

  fs.writeFileSync('/root/output/leaf_parts_index.json', JSON.stringify(index, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
EOF

node /root/build_transfer3.js
