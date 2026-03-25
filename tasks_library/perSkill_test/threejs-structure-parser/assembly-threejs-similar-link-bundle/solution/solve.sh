#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/solve_bundle.mjs <<'EOF'
import fs from 'fs';
import path from 'path';
import * as THREE from 'three';
import { pathToFileURL } from 'url';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const inputPath = '/root/data/assembly_scene.js';
const outputDir = '/root/output';
const partMeshDir = path.join(outputDir, 'part_meshes');
const linkDir = path.join(outputDir, 'links');

const sceneModule = await import(pathToFileURL(inputPath).href);
const root = sceneModule.createScene();
if (!root) {
    throw new Error('createScene() did not return a scene root');
}

root.updateMatrixWorld(true);

fs.mkdirSync(partMeshDir, { recursive: true });
fs.mkdirSync(linkDir, { recursive: true });

const exporter = new OBJExporter();

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

function exportGeometry(geometry, name, filePath) {
    const tempMesh = new THREE.Mesh(geometry);
    tempMesh.name = name;
    fs.writeFileSync(filePath, exporter.parse(tempMesh));
}

const partMap = new Map();
root.traverse((object) => {
    if (object.isGroup && object.name) {
        partMap.set(object.name, {
            group: object,
            parent_part: null,
            meshes: [],
        });
    }
});

for (const part of partMap.values()) {
    let parent = part.group.parent;
    while (parent) {
        if (parent.isGroup && parent.name) {
            part.parent_part = parent.name;
            break;
        }
        parent = parent.parent;
    }
}

root.traverse((object) => {
    if (!object.isMesh) {
        return;
    }
    let parent = object.parent;
    while (parent) {
        if (parent.isGroup && parent.name) {
            const owner = partMap.get(parent.name);
            if (owner) {
                owner.meshes.push(object);
            }
            break;
        }
        parent = parent.parent;
    }
});

const parts = Array.from(partMap.entries())
    .filter(([, part]) => part.meshes.length > 0)
    .sort((a, b) => a[0].localeCompare(b[0]));

const indexParts = [];

for (const [partName, part] of parts) {
    const meshRecords = part.meshes
        .map((mesh) => ({
            mesh,
            meshName: mesh.name,
        }))
        .sort((a, b) => a.meshName.localeCompare(b.meshName));

    const partDir = path.join(partMeshDir, partName);
    fs.mkdirSync(partDir, { recursive: true });

    const geometries = [];
    for (const record of meshRecords) {
        const geometry = bakeGeometry(record.mesh);
        geometries.push(geometry);
        const relativePath = path.posix.join('part_meshes', partName, `${record.meshName}.obj`);
        exportGeometry(
            geometry,
            record.meshName,
            path.join(outputDir, relativePath),
        );
    }

    const merged = mergeGeometries(geometries, false);
    const mergedRelativePath = path.posix.join('links', `${partName}.obj`);
    exportGeometry(merged, partName, path.join(outputDir, mergedRelativePath));

    indexParts.push({
        part_name: partName,
        parent_part: part.parent_part,
        mesh_count: meshRecords.length,
        mesh_names: meshRecords.map((record) => record.meshName),
        mesh_obj_files: meshRecords.map((record) =>
            path.posix.join('part_meshes', partName, `${record.meshName}.obj`)
        ),
        merged_obj_file: mergedRelativePath,
    });
}

fs.writeFileSync(
    path.join(outputDir, 'link_index.json'),
    JSON.stringify(
        {
            scene_file: 'assembly_scene.js',
            parts: indexParts,
        },
        null,
        2,
    ),
);
EOF

node /root/solve_bundle.mjs
