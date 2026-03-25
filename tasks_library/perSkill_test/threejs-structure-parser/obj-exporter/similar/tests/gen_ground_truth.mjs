import * as THREE from "three";
import fs from "fs";
import { pathToFileURL } from "url";
import { OBJExporter } from "three/examples/jsm/exporters/OBJExporter.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

const INPUT_PATH = "/root/data/similar_scene.mjs";
const GT_ROOT = "/root/ground_truth";
const MESH_DIR = `${GT_ROOT}/component_meshes`;
const LINK_DIR = `${GT_ROOT}/component_links`;
const MANIFEST_PATH = `${GT_ROOT}/manifest.json`;

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
    Object.entries(componentMap).filter(([, entry]) => entry.meshes.length > 0)
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

function exportMesh(exporter, mesh, filepath, nameOverride) {
  const geometry = cloneWorldGeometry(mesh);
  const tempMesh = new THREE.Mesh(geometry);
  tempMesh.name = nameOverride;
  fs.writeFileSync(filepath, exporter.parse(tempMesh));
}

function mergeMeshes(meshes) {
  const geometries = meshes.map((mesh) => cloneWorldGeometry(mesh));
  return new THREE.Mesh(mergeGeometries(geometries, false));
}

const sceneModule = await import(pathToFileURL(INPUT_PATH).href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

fs.rmSync(GT_ROOT, { recursive: true, force: true });
fs.mkdirSync(MESH_DIR, { recursive: true });
fs.mkdirSync(LINK_DIR, { recursive: true });

const exporter = new OBJExporter();
const componentMap = collectComponentMeshes(root);
const components = [];

for (const componentName of Object.keys(componentMap).sort()) {
  const meshes = componentMap[componentName].meshes.slice().sort((a, b) => a.name.localeCompare(b.name));
  const componentDir = `${MESH_DIR}/${componentName}`;
  fs.mkdirSync(componentDir, { recursive: true });

  const meshFiles = [];
  for (const mesh of meshes) {
    const meshName = mesh.name || "unnamed_mesh";
    const filename = `${meshName}.obj`;
    exportMesh(exporter, mesh, `${componentDir}/${filename}`, meshName);
    meshFiles.push(filename);
  }

  const mergedMesh = mergeMeshes(meshes);
  mergedMesh.name = componentName;
  const mergedPath = `${LINK_DIR}/${componentName}.obj`;
  fs.writeFileSync(mergedPath, exporter.parse(mergedMesh));

  components.push({
    component: componentName,
    mesh_dir: `/root/output/component_meshes/${componentName}`,
    merged_obj: `/root/output/component_links/${componentName}.obj`,
    mesh_files: meshFiles,
    mesh_count: meshFiles.length
  });
}

const manifest = {
  scene: root.name,
  components,
  totals: {
    component_count: components.length,
    mesh_count: components.reduce((sum, entry) => sum + entry.mesh_count, 0)
  },
  tool_called: ["component_obj_export"]
};

fs.writeFileSync(MANIFEST_PATH, `${JSON.stringify(manifest, null, 2)}\n`);
