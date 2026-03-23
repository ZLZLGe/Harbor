import fs from 'fs';
import { pathToFileURL } from 'url';
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const INPUT_PATH = '/root/data/fabrication_scene.js';
const GT_DIR = '/root/ground_truth';
const LINKS_DIR = `${GT_DIR}/fabrication_links`;
const MANIFEST_PATH = `${GT_DIR}/fabrication_manifest.json`;
const AXIS_MATRIX = new THREE.Matrix4().makeRotationX(-Math.PI / 2);

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
        meshes: [],
      });
    }
  });

  root.traverse((obj) => {
    if (!obj.isMesh) {
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
    .filter((part) => part.meshes.length > 0)
    .sort((a, b) => a.group.name.localeCompare(b.group.name));
}

function bakeGeometry(mesh) {
  let geometry = mesh.geometry.clone();
  geometry.applyMatrix4(mesh.matrixWorld);
  geometry.applyMatrix4(AXIS_MATRIX);
  if (geometry.index) {
    geometry = geometry.toNonIndexed();
  }
  if (!geometry.attributes.normal) {
    geometry.computeVertexNormals();
  }
  return geometry;
}

function exportMergedPart(exporter, partName, meshes) {
  const merged = mergeGeometries(meshes.map((mesh) => bakeGeometry(mesh)), false);
  const outMesh = new THREE.Mesh(merged);
  outMesh.name = partName;
  fs.writeFileSync(`${LINKS_DIR}/${partName}.obj`, exporter.parse(outMesh));
}

async function main() {
  const mod = await import(pathToFileURL(INPUT_PATH).href);
  const root = mod.createScene();
  root.updateMatrixWorld(true);

  fs.rmSync(GT_DIR, { recursive: true, force: true });
  fs.mkdirSync(LINKS_DIR, { recursive: true });

  const exporter = new OBJExporter();
  const manifest = { parts: [] };

  for (const part of discoverParts(root)) {
    const sourceMeshes = part.meshes
      .map((mesh, index) => mesh.name || `unnamed_mesh_${index}`)
      .sort((a, b) => a.localeCompare(b));

    exportMergedPart(exporter, part.group.name, part.meshes);

    manifest.parts.push({
      part_name: part.group.name,
      parent_part: part.parentPart,
      mesh_count: part.meshes.length,
      source_meshes: sourceMeshes,
      link_obj: `fabrication_links/${part.group.name}.obj`,
    });
  }

  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
