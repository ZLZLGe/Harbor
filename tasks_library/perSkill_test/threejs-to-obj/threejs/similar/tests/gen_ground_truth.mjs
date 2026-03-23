import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
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

  return Array.from(parts.values())
    .filter((entry) => entry.meshes.length > 0)
    .sort((a, b) => a.group.name.localeCompare(b.group.name));
}

function exportPartObj(meshes, outputPath) {
  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
  const geometries = [];

  for (const mesh of meshes) {
    let geometry = mesh.geometry.clone();
    geometry.applyMatrix4(mesh.matrixWorld);
    geometry.applyMatrix4(axisMatrix);
    if (geometry.index) {
      geometry = geometry.toNonIndexed();
    }
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }
    geometries.push(geometry);
  }

  const merged = mergeGeometries(geometries, false);
  const exporter = new OBJExporter();
  fs.writeFileSync(outputPath, exporter.parse(new THREE.Mesh(merged)));
}

async function main() {
  const sceneModule = await import(pathToFileURL('/root/data/cabinet_scene.js').href);
  const root = sceneModule.createScene();
  root.updateMatrixWorld(true);

  fs.mkdirSync('/root/ground_truth/parts', { recursive: true });
  const entries = buildPartEntries(root);
  const manifest = { parts: [] };

  for (const entry of entries) {
    const partName = entry.group.name;
    const outputPath = `/root/ground_truth/parts/${partName}.obj`;
    exportPartObj(entry.meshes, outputPath);
    manifest.parts.push({
      part_name: partName,
      mesh_names: entry.meshes.map((mesh) => mesh.name).sort(),
      obj_path: outputPath,
    });
  }

  fs.writeFileSync('/root/ground_truth/part_manifest.json', JSON.stringify(manifest, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
