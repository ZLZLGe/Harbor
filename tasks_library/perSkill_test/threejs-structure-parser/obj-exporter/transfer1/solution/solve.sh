#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/transfer1_export.mjs <<'EOF'
import * as THREE from "three";
import fs from "fs";
import { pathToFileURL } from "url";
import { OBJExporter } from "three/examples/jsm/exporters/OBJExporter.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

const INPUT_PATH = "/root/data/transfer1_scene.mjs";
const PLAN_PATH = "/root/data/transfer1_export_plan.json";
const OUTPUT_DIR = "/root/output/crates";
const REPORT_PATH = "/root/transfer1_crate_summary.json";

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
const plan = JSON.parse(fs.readFileSync(PLAN_PATH, "utf-8"));
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

const componentMap = collectComponentMeshes(root);
fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const crates = [];

for (const request of plan.requests) {
  const meshes = (componentMap[request.component]?.meshes ?? []).slice().sort((a, b) => a.name.localeCompare(b.name));
  if (meshes.length === 0) {
    throw new Error(`missing component ${request.component}`);
  }
  const merged = new THREE.Mesh(mergeGeometries(meshes.map((mesh) => cloneWorldGeometry(mesh)), false));
  merged.name = request.crate_label;
  const objData = exporter.parse(merged);
  const targetObj = `${OUTPUT_DIR}/${request.crate_label}.obj`;
  fs.writeFileSync(targetObj, objData);
  crates.push({
    crate_label: request.crate_label,
    source_component: request.component,
    target_obj: targetObj,
    mesh_count: meshes.length,
    vertex_count: countVertices(objData)
  });
}

const report = {
  scene: root.name,
  requests: plan.requests.map((request) => request.component),
  crates,
  tool_called: ["crate_component_export"]
};

fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`);
EOF

node /root/transfer1_export.mjs
