import fs from "fs";
import * as THREE from "three";
import { pathToFileURL } from "url";

const sceneModule = await import(pathToFileURL("/root/data/transfer1_scene.js").href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

const namedGroups = new Map();
root.traverse((obj) => {
  if (obj.isGroup && obj.name && obj !== root) {
    namedGroups.set(obj.name, obj);
  }
});

const triangleCount = (geometry) => {
  if (geometry.index) {
    return geometry.index.count / 3;
  }
  return geometry.attributes.position.count / 3;
};

const summarizePart = (group) => {
  let meshCount = 0;
  let instancedInstanceCount = 0;
  let ownedTriangleCount = 0;

  group.traverse((obj) => {
    if (obj !== group && obj.isGroup && obj.name && namedGroups.has(obj.name)) {
      return;
    }
    if (obj.isInstancedMesh) {
      const count = obj.count ?? obj.instanceCount ?? 0;
      instancedInstanceCount += count;
      ownedTriangleCount += triangleCount(obj.geometry) * count;
    } else if (obj.isMesh) {
      meshCount += 1;
      ownedTriangleCount += triangleCount(obj.geometry);
    }
  });

  return {
    meshCount,
    instancedInstanceCount,
    ownedTriangleCount
  };
};

const hasOwnedGeometry = (group) => {
  const summary = summarizePart(group);
  return summary.meshCount > 0 || summary.instancedInstanceCount > 0;
};

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

const includedParts = new Set(
  Array.from(namedGroups.entries())
    .filter(([, group]) => hasOwnedGeometry(group))
    .map(([name]) => name)
);

const parts = Array.from(includedParts)
  .sort()
  .map((name) => {
    const group = namedGroups.get(name);
    const summary = summarizePart(group);
    const childParts = Array.from(includedParts)
      .filter((candidate) => {
        const childGroup = namedGroups.get(candidate);
        return childGroup !== group && findParentPart(childGroup) === name;
      })
      .sort();
    return {
      name,
      parent: findParentPart(group),
      child_parts: childParts,
      mesh_count: summary.meshCount,
      instanced_instance_count: summary.instancedInstanceCount,
      owned_triangle_count: summary.ownedTriangleCount
    };
  });

fs.writeFileSync(
  process.stdout.fd,
  JSON.stringify(
    {
      scene_name: root.name,
      parts
    },
    null,
    2
  )
);
