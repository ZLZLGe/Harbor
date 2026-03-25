#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/export_transfer3.js <<'EOF'
import * as THREE from "three";
import fs from "fs";
import { pathToFileURL } from "url";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { OBJExporter } from "three/examples/jsm/exporters/OBJExporter.js";

async function buildScene() {
  const factories = await import(pathToFileURL("/root/data/component_factory.js").href);
  const plan = JSON.parse(fs.readFileSync("/root/data/assembly_plan.json", "utf-8"));

  const root = new THREE.Group();
  root.name = "modular_display";

  for (const entry of plan) {
    const factory = factories[entry.factory];
    if (typeof factory !== "function") {
      throw new Error(`Unknown factory: ${entry.factory}`);
    }
    const component = factory();
    component.name = entry.name ?? component.name;
    component.position.set(...entry.position);
    component.rotation.set(...entry.rotation);
    component.scale.set(...entry.scale);
    root.add(component);
  }

  return root;
}

async function main() {
  const root = await buildScene();
  root.updateMatrixWorld(true);

  const geometries = [];
  const instanceMatrix = new THREE.Matrix4();
  const combinedMatrix = new THREE.Matrix4();
  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);

  function addGeometry(source, matrix) {
    let geometry = source.clone();
    geometry.applyMatrix4(matrix);
    geometry.applyMatrix4(axisMatrix);
    if (geometry.index) {
      geometry = geometry.toNonIndexed();
    }
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }
    geometries.push(geometry);
  }

  root.traverse((node) => {
    if (node.isInstancedMesh) {
      const count = node.count ?? node.instanceCount ?? 0;
      for (let index = 0; index < count; index += 1) {
        node.getMatrixAt(index, instanceMatrix);
        combinedMatrix.copy(node.matrixWorld).multiply(instanceMatrix);
        addGeometry(node.geometry, combinedMatrix);
      }
      return;
    }
    if (node instanceof THREE.Mesh) {
      addGeometry(node.geometry, node.matrixWorld);
    }
  });

  const merged = mergeGeometries(geometries, false);
  const exporter = new OBJExporter();
  fs.writeFileSync("/root/output/modular_display.obj", exporter.parse(new THREE.Mesh(merged)));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
EOF

node /root/export_transfer3.js
