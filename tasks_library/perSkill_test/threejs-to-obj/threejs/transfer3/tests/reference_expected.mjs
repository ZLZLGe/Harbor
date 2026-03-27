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

const rows = [];
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

  rows.push({
    name,
    parent: findParentPart(part),
    piece_count: String(geometries.length),
    vertex_count: String(vertexCount),
    face_count: String(faceCount),
    min_x: format(min[0]),
    min_y: format(min[1]),
    min_z: format(min[2]),
    max_x: format(max[0]),
    max_y: format(max[1]),
    max_z: format(max[2])
  });
}

console.log(JSON.stringify(rows, null, 2));
