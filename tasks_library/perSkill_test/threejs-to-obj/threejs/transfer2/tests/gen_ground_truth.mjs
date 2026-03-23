import * as THREE from 'three';
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

function directChildParts(group) {
  const children = [];
  group.traverse((obj) => {
    if (obj === group || !(obj.isGroup && obj.name)) {
      return;
    }
    let parent = obj.parent;
    while (parent && !(parent.isGroup && parent.name)) {
      parent = parent.parent;
    }
    if (parent === group) {
      children.push(obj.name);
    }
  });
  return children.sort();
}

function parentPartName(group) {
  let parent = group.parent;
  while (parent && !(parent.isGroup && parent.name)) {
    parent = parent.parent;
  }
  return parent?.name ?? null;
}

function triangleCount(meshes) {
  let total = 0;
  for (const mesh of meshes) {
    const geometry = mesh.geometry;
    if (geometry.index) {
      total += geometry.index.count / 3;
    } else {
      total += geometry.attributes.position.count / 3;
    }
  }
  return total;
}

function worldBounds(meshes) {
  const min = new THREE.Vector3(Infinity, Infinity, Infinity);
  const max = new THREE.Vector3(-Infinity, -Infinity, -Infinity);

  for (const mesh of meshes) {
    let geometry = mesh.geometry.clone();
    geometry.applyMatrix4(mesh.matrixWorld);
    const positions = geometry.attributes.position;
    for (let index = 0; index < positions.count; index += 1) {
      const vector = new THREE.Vector3().fromBufferAttribute(positions, index);
      min.min(vector);
      max.max(vector);
    }
  }

  return {
    min: [Number(min.x.toFixed(6)), Number(min.y.toFixed(6)), Number(min.z.toFixed(6))],
    max: [Number(max.x.toFixed(6)), Number(max.y.toFixed(6)), Number(max.z.toFixed(6))],
  };
}

async function main() {
  const sceneModule = await import(pathToFileURL('/root/data/line_fixture.js').href);
  const root = sceneModule.createScene();
  root.updateMatrixWorld(true);

  const parts = buildPartEntries(root);
  const result = { parts: [] };

  for (const entry of Array.from(parts.values()).sort((a, b) => a.group.name.localeCompare(b.group.name))) {
    if (entry.meshes.length === 0) {
      continue;
    }
    const bounds = worldBounds(entry.meshes);
    result.parts.push({
      part_name: entry.group.name,
      parent_part: parentPartName(entry.group),
      child_parts: directChildParts(entry.group),
      owned_meshes: entry.meshes.map((mesh) => mesh.name).sort(),
      mesh_count: entry.meshes.length,
      triangle_count: triangleCount(entry.meshes),
      world_bbox_min: bounds.min,
      world_bbox_max: bounds.max,
    });
  }

  fs.mkdirSync('/root/ground_truth', { recursive: true });
  fs.writeFileSync('/root/ground_truth/link_audit.json', JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
