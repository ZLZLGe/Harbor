import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { pathToFileURL } from "url";

const sceneModule = await import(pathToFileURL("/root/data/similar_scene.js").href);
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

const round = (value) => Number(value.toFixed(6));

const summarizeGeometry = (geometry) => {
  const position = geometry.attributes.position;
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  const sum = [0, 0, 0];
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
    sum[0] += x;
    sum[1] += y;
    sum[2] += z;
  }
  return {
    vertex_count: position.count,
    face_count: position.count / 3,
    min: min.map(round),
    max: max.map(round),
    centroid: sum.map((value) => round(value / position.count))
  };
};

const parts = [];
for (const name of Array.from(namedGroups.keys()).sort()) {
  const part = namedGroups.get(name);
  const geometries = collectOwnedGeometry(part);
  if (!geometries.length) {
    continue;
  }
  const merged = mergeGeometries(geometries, false);
  parts.push({
    name,
    parent: findParentPart(part),
    obj_file: `links/${name}.obj`,
    ...summarizeGeometry(merged)
  });
}

console.log(JSON.stringify({ scene_name: root.name, parts }, null, 2));
