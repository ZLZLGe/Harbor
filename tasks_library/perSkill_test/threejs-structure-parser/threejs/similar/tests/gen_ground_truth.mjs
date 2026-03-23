import fs from 'fs';
import { pathToFileURL } from 'url';
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const INPUT_PATH = '/root/data/ride_scene.js';
const GT_DIR = '/root/ground_truth';
const PART_MESHES_DIR = `${GT_DIR}/part_meshes`;
const LINKS_DIR = `${GT_DIR}/links`;
const INVENTORY_PATH = `${GT_DIR}/part_inventory.json`;

function collectParts(root) {
  const partMap = new Map();

  root.traverse((obj) => {
    if (obj.isGroup && obj.name) {
      let namedParent = obj.parent;
      while (namedParent && !(namedParent.isGroup && namedParent.name)) {
        namedParent = namedParent.parent;
      }
      partMap.set(obj.name, {
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
    if (parent && partMap.has(parent.name)) {
      partMap.get(parent.name).meshes.push(obj);
    }
  });

  return Array.from(partMap.values())
    .filter((part) => part.meshes.length > 0)
    .sort((a, b) => a.group.name.localeCompare(b.group.name));
}

function bakeGeometry(mesh) {
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

function exportMesh(exporter, mesh, outPath, name) {
  const bakedMesh = new THREE.Mesh(bakeGeometry(mesh));
  bakedMesh.name = name;
  fs.writeFileSync(outPath, exporter.parse(bakedMesh));
}

function exportMergedLink(exporter, meshes, outPath, name) {
  const merged = mergeGeometries(meshes.map((mesh) => bakeGeometry(mesh)), false);
  const bakedMesh = new THREE.Mesh(merged);
  bakedMesh.name = name;
  fs.writeFileSync(outPath, exporter.parse(bakedMesh));
}

async function main() {
  const mod = await import(pathToFileURL(INPUT_PATH).href);
  const root = mod.createScene();
  root.updateMatrixWorld(true);

  fs.rmSync(GT_DIR, { recursive: true, force: true });
  fs.mkdirSync(PART_MESHES_DIR, { recursive: true });
  fs.mkdirSync(LINKS_DIR, { recursive: true });

  const exporter = new OBJExporter();
  const inventory = { parts: [] };

  for (const part of collectParts(root)) {
    const partName = part.group.name;
    const meshDir = `${PART_MESHES_DIR}/${partName}`;
    const linkObj = `${LINKS_DIR}/${partName}.obj`;
    fs.mkdirSync(meshDir, { recursive: true });

    const meshNames = part.meshes
      .map((mesh, index) => mesh.name || `unnamed_mesh_${index}`)
      .sort((a, b) => a.localeCompare(b));

    const meshesByName = new Map(
      part.meshes.map((mesh, index) => [mesh.name || `unnamed_mesh_${index}`, mesh]),
    );

    for (const meshName of meshNames) {
      exportMesh(exporter, meshesByName.get(meshName), `${meshDir}/${meshName}.obj`, meshName);
    }

    exportMergedLink(exporter, part.meshes, linkObj, partName);

    inventory.parts.push({
      part_name: partName,
      parent_part: part.parentPart,
      mesh_names: meshNames,
      part_mesh_dir: `part_meshes/${partName}`,
      link_obj: `links/${partName}.obj`,
    });
  }

  fs.writeFileSync(INVENTORY_PATH, JSON.stringify(inventory, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
