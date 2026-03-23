import * as THREE from "three";
import fs from "fs";
import { pathToFileURL } from "url";
import { OBJExporter } from "three/examples/jsm/exporters/OBJExporter.js";

const INPUT_PATH = "/root/data/transfer2_scene.mjs";
const GT_ROOT = "/root/ground_truth";
const OUTPUT_DIR = `${GT_ROOT}/audit_meshes`;
const LEDGER_PATH = `${GT_ROOT}/ledger.csv`;

function collectComponentMeshes(root) {
  const componentMap = {};
  root.traverse((obj) => {
    if (obj instanceof THREE.Group && obj.name) {
      componentMap[obj.name] = { meshes: [] };
    }
  });
  root.traverse((obj) => {
    if (!(obj instanceof THREE.Mesh)) {
      return;
    }
    let parent = obj.parent;
    while (parent && !(parent instanceof THREE.Group && parent.name)) {
      parent = parent.parent;
    }
    if (parent && componentMap[parent.name]) {
      componentMap[parent.name].meshes.push(obj);
    }
  });
  return Object.fromEntries(
    Object.entries(componentMap).filter(([, value]) => value.meshes.length > 0)
  );
}

function cloneWorldGeometry(mesh) {
  let geometry = mesh.geometry.clone();
  geometry.applyMatrix4(mesh.matrixWorld);
  if (geometry.index) {
    geometry = geometry.toNonIndexed();
  }
  if (!geometry.attributes.normal) {
    geometry.computeVertexNormals();
  }
  return geometry;
}

function summarizeGeometry(geometry) {
  const positions = geometry.getAttribute("position");
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;
  for (let index = 0; index < positions.count; index += 1) {
    const x = positions.getX(index);
    const y = positions.getY(index);
    const z = positions.getZ(index);
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    minZ = Math.min(minZ, z);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
    maxZ = Math.max(maxZ, z);
  }
  return {
    vertexCount: positions.count,
    faceCount: positions.count / 3,
    minX,
    minY,
    minZ,
    maxX,
    maxY,
    maxZ
  };
}

const exporter = new OBJExporter();
const sceneModule = await import(pathToFileURL(INPUT_PATH).href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

const componentMap = collectComponentMeshes(root);
fs.rmSync(GT_ROOT, { recursive: true, force: true });
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const rows = [
  "component,mesh_file,vertex_count,face_count,min_x,min_y,min_z,max_x,max_y,max_z"
];

for (const componentName of Object.keys(componentMap).sort()) {
  const componentDir = `${OUTPUT_DIR}/${componentName}`;
  fs.mkdirSync(componentDir, { recursive: true });
  const meshes = componentMap[componentName].meshes.slice().sort((a, b) => a.name.localeCompare(b.name));
  for (const mesh of meshes) {
    const meshName = mesh.name || "unnamed_mesh";
    const filename = `${meshName}.obj`;
    const geometry = cloneWorldGeometry(mesh);
    const tempMesh = new THREE.Mesh(geometry);
    tempMesh.name = meshName;
    fs.writeFileSync(`${componentDir}/${filename}`, exporter.parse(tempMesh));
    const summary = summarizeGeometry(geometry);
    rows.push([
      componentName,
      filename,
      summary.vertexCount,
      summary.faceCount,
      summary.minX.toFixed(6),
      summary.minY.toFixed(6),
      summary.minZ.toFixed(6),
      summary.maxX.toFixed(6),
      summary.maxY.toFixed(6),
      summary.maxZ.toFixed(6)
    ].join(","));
  }
}

fs.writeFileSync(LEDGER_PATH, `${rows.join("\n")}\n`);
