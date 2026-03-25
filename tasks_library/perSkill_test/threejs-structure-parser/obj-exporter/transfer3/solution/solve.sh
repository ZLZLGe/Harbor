#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/transfer3_export.mjs <<'EOF'
import * as THREE from "three";
import fs from "fs";
import { pathToFileURL } from "url";
import { OBJExporter } from "three/examples/jsm/exporters/OBJExporter.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

const INPUT_PATH = "/root/data/transfer3_scene.mjs";
const RULES_PATH = "/root/data/transfer3_bundle_rules.json";
const OUTPUT_DIR = "/root/output/bundles";
const REPORT_PATH = "/root/transfer3_bundle_report.json";

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
  return componentMap;
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

function countVertices(objString) {
  return objString.split("\n").filter((line) => line.startsWith("v ")).length;
}

const exporter = new OBJExporter();
const sceneModule = await import(pathToFileURL(INPUT_PATH).href);
const rules = JSON.parse(fs.readFileSync(RULES_PATH, "utf-8"));
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

const componentMap = collectComponentMeshes(root);
fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const bundles = [];

for (const entry of rules.bundles) {
  const meshes = [];
  for (const componentName of entry.components) {
    const componentMeshes = componentMap[componentName]?.meshes ?? [];
    if (componentMeshes.length === 0) {
      throw new Error(`missing component ${componentName}`);
    }
    meshes.push(...componentMeshes);
  }
  const orderedMeshes = meshes.slice().sort((a, b) => a.name.localeCompare(b.name));
  const merged = new THREE.Mesh(mergeGeometries(orderedMeshes.map((mesh) => cloneWorldGeometry(mesh)), false));
  merged.name = entry.bundle;
  const objData = exporter.parse(merged);
  const targetObj = `${OUTPUT_DIR}/${entry.bundle}.obj`;
  fs.writeFileSync(targetObj, objData);

  bundles.push({
    bundle: entry.bundle,
    components: entry.components,
    target_obj: targetObj,
    mesh_count: orderedMeshes.length,
    vertex_count: countVertices(objData)
  });
}

const report = {
  scene: root.name,
  bundles,
  tool_called: ["bundle_obj_export"]
};

fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`);
EOF

node /root/transfer3_export.mjs
