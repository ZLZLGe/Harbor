import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { pathToFileURL } from "url";

const sceneModule = await import(pathToFileURL("/root/data/transfer2_scene.js").href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

const jointMap = JSON.parse(await (await import("node:fs/promises")).readFile("/root/data/joint_types.json", "utf8"));

const namedGroups = new Map();
root.traverse((obj) => {
  if (obj.isGroup && obj.name && obj !== root) {
    namedGroups.set(obj.name, obj);
  }
});

const tempMatrix = new THREE.Matrix4();
const instanceMatrix = new THREE.Matrix4();

const addGeometry = (geometries, geometry, matrix) => {
  let baked = geometry.clone();
  baked.applyMatrix4(matrix);
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

const findParentLink = (group) => {
  let current = group.parent;
  while (current) {
    if (current.isGroup && current.name && current !== root && namedGroups.has(current.name)) {
      return current.name;
    }
    current = current.parent;
  }
  return null;
};

const round = (value) => Number(value.toFixed(6));
const meshMetrics = [];
for (const name of Array.from(namedGroups.keys()).sort()) {
  const group = namedGroups.get(name);
  const geometries = collectOwnedGeometry(group);
  if (!geometries.length) {
    continue;
  }
  const merged = mergeGeometries(geometries, false);
  const position = merged.attributes.position;
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
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
  meshMetrics.push({
    name,
    vertex_count: position.count,
    face_count: merged.index ? merged.index.count / 3 : position.count / 3,
    min: min.map(round),
    max: max.map(round)
  });
}

const joints = meshMetrics
  .map((link) => {
    const parent = findParentLink(namedGroups.get(link.name));
    if (!parent) {
      return null;
    }
    return {
      name: `joint_${link.name}`,
      parent,
      child: link.name,
      type: jointMap[link.name] || "fixed"
    };
  })
  .filter(Boolean)
  .sort((a, b) => a.name.localeCompare(b.name));

console.log(
  JSON.stringify(
    {
      robot_name: root.name,
      links: meshMetrics.map((item) => item.name),
      joints,
      meshes: meshMetrics
    },
    null,
    2
  )
);
