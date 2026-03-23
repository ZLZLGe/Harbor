import fs from 'fs';
import { pathToFileURL } from 'url';
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const INPUT_PATH = '/root/data/robot_scene.js';
const GT_DIR = '/root/ground_truth';
const MESH_DIR = `${GT_DIR}/meshes`;
const URDF_PATH = `${GT_DIR}/robot_arm.urdf`;

function discoverLinks(root) {
  const links = new Map();

  root.traverse((obj) => {
    if (obj.isGroup && obj.name) {
      let namedParent = obj.parent;
      while (namedParent && !(namedParent.isGroup && namedParent.name)) {
        namedParent = namedParent.parent;
      }
      links.set(obj.name, {
        group: obj,
        parentLink: namedParent ? namedParent.name : null,
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
    if (parent && links.has(parent.name)) {
      links.get(parent.name).meshes.push(obj);
    }
  });

  return Array.from(links.values())
    .filter((entry) => entry.meshes.length > 0)
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

function exportLinkMesh(exporter, linkName, meshes) {
  const merged = mergeGeometries(meshes.map((mesh) => bakeGeometry(mesh)), false);
  const mergedMesh = new THREE.Mesh(merged);
  mergedMesh.name = linkName;
  fs.writeFileSync(`${MESH_DIR}/${linkName}.obj`, exporter.parse(mergedMesh));
}

function renderUrdf(linkEntries) {
  const lines = ['<?xml version="1.0"?>', '<robot name="inspection_robot">'];

  for (const link of linkEntries) {
    lines.push(`  <link name="${link.group.name}">`);
    lines.push('    <visual>');
    lines.push('      <geometry>');
    lines.push(`        <mesh filename="meshes/${link.group.name}.obj"/>`);
    lines.push('      </geometry>');
    lines.push('    </visual>');
    lines.push('  </link>');
  }

  const jointEntries = linkEntries
    .filter((link) => link.parentLink)
    .map((link) => ({
      name: `${link.parentLink}__to__${link.group.name}`,
      parent: link.parentLink,
      child: link.group.name,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));

  for (const joint of jointEntries) {
    lines.push(`  <joint name="${joint.name}" type="fixed">`);
    lines.push(`    <parent link="${joint.parent}"/>`);
    lines.push(`    <child link="${joint.child}"/>`);
    lines.push('    <origin xyz="0 0 0" rpy="0 0 0"/>');
    lines.push('  </joint>');
  }

  lines.push('</robot>');
  return `${lines.join('\n')}\n`;
}

async function main() {
  const mod = await import(pathToFileURL(INPUT_PATH).href);
  const root = mod.createScene();
  root.updateMatrixWorld(true);

  fs.rmSync(GT_DIR, { recursive: true, force: true });
  fs.mkdirSync(MESH_DIR, { recursive: true });

  const exporter = new OBJExporter();
  const links = discoverLinks(root);

  for (const link of links) {
    exportLinkMesh(exporter, link.group.name, link.meshes);
  }

  fs.writeFileSync(URDF_PATH, renderUrdf(links));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
