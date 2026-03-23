import fs from 'fs';
import { pathToFileURL } from 'url';
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';

const INPUT_PATH = '/root/data/rack_scene.js';
const GT_DIR = '/root/ground_truth';
const INSTANCES_DIR = `${GT_DIR}/instances`;
const REPORT_PATH = `${GT_DIR}/instance_report.json`;

function discoverParts(root) {
  const parts = new Map();

  root.traverse((obj) => {
    if (obj.isGroup && obj.name) {
      let namedParent = obj.parent;
      while (namedParent && !(namedParent.isGroup && namedParent.name)) {
        namedParent = namedParent.parent;
      }
      parts.set(obj.name, {
        group: obj,
        parentPart: namedParent ? namedParent.name : null,
        exports: [],
      });
    }
  });

  return parts;
}

function nearestNamedAncestor(obj) {
  let current = obj.parent;
  while (current && !(current.isGroup && current.name)) {
    current = current.parent;
  }
  return current ? current.name : null;
}

function bakeInstanceGeometry(object, index) {
  let geometry = object.geometry.clone();
  const instanceMatrix = new THREE.Matrix4();
  const worldMatrix = new THREE.Matrix4();
  object.getMatrixAt(index, instanceMatrix);
  worldMatrix.copy(object.matrixWorld).multiply(instanceMatrix);
  geometry.applyMatrix4(worldMatrix);
  if (geometry.index) {
    geometry = geometry.toNonIndexed();
  }
  if (!geometry.attributes.normal) {
    geometry.computeVertexNormals();
  }
  return geometry;
}

async function main() {
  const mod = await import(pathToFileURL(INPUT_PATH).href);
  const root = mod.createScene();
  root.updateMatrixWorld(true);

  fs.rmSync(GT_DIR, { recursive: true, force: true });
  fs.mkdirSync(INSTANCES_DIR, { recursive: true });

  const exporter = new OBJExporter();
  const parts = discoverParts(root);

  root.traverse((obj) => {
    if (!obj.isInstancedMesh) {
      return;
    }
    const partName = nearestNamedAncestor(obj);
    if (!partName || !parts.has(partName)) {
      return;
    }

    const partDir = `${INSTANCES_DIR}/${partName}`;
    fs.mkdirSync(partDir, { recursive: true });

    for (let index = 0; index < obj.count; index += 1) {
      const exportName = `${obj.name || 'instance'}__${String(index).padStart(2, '0')}.obj`;
      const mesh = new THREE.Mesh(bakeInstanceGeometry(obj, index));
      mesh.name = exportName.replace(/\.obj$/, '');
      fs.writeFileSync(`${partDir}/${exportName}`, exporter.parse(mesh));
      parts.get(partName).exports.push(`instances/${partName}/${exportName}`);
    }
  });

  const report = {
    parts: Array.from(parts.entries())
      .map(([partName, entry]) => ({
        part_name: partName,
        parent_part: entry.parentPart,
        exported_files: entry.exports.sort((a, b) => a.localeCompare(b)),
        export_count: entry.exports.length,
      }))
      .filter((entry) => entry.export_count > 0)
      .sort((a, b) => a.part_name.localeCompare(b.part_name)),
  };

  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
