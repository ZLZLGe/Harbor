#!/bin/bash
set -euo pipefail

mkdir -p /root/output/meshes

cat > /root/build_transfer1.js <<'EOF'
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

  return Array.from(parts.values())
    .filter((entry) => entry.meshes.length > 0)
    .sort((a, b) => a.group.name.localeCompare(b.group.name));
}

function parentPartName(group) {
  let parent = group.parent;
  while (parent && !(parent.isGroup && parent.name)) {
    parent = parent.parent;
  }
  return parent?.name ?? null;
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

function buildUrdf(entries) {
  const linkBlocks = [];
  const jointBlocks = [];

  for (const entry of entries) {
    const name = entry.group.name;
    linkBlocks.push(
      `  <link name="${name}">\n` +
      `    <visual>\n` +
      `      <geometry>\n` +
      `        <mesh filename="meshes/${name}.obj"/>\n` +
      `      </geometry>\n` +
      `    </visual>\n` +
      `  </link>`
    );

    const parent = parentPartName(entry.group);
    if (parent) {
      const jointName = `${parent}_to_${name}`;
      jointBlocks.push(
        `  <joint name="${jointName}" type="fixed">\n` +
        `    <parent link="${parent}"/>\n` +
        `    <child link="${name}"/>\n` +
        `    <origin xyz="0 0 0" rpy="0 0 0"/>\n` +
        `  </joint>`
      );
    }
  }

  jointBlocks.sort();

  return [
    '<?xml version="1.0"?>',
    '<robot name="inspection_rig">',
    ...linkBlocks,
    ...jointBlocks,
    '</robot>',
    '',
  ].join('\n');
}

async function main() {
  const sceneModule = await import(pathToFileURL('/root/data/inspection_rig.js').href);
  const root = sceneModule.createScene();
  root.updateMatrixWorld(true);

  const entries = buildPartEntries(root);
  for (const entry of entries) {
    exportPartObj(entry.meshes, `/root/output/meshes/${entry.group.name}.obj`);
  }

  fs.writeFileSync('/root/output/inspection_rig.urdf', buildUrdf(entries));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
EOF

node /root/build_transfer1.js
