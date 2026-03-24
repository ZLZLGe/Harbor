import fs from 'fs';
import path from 'path';
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { pathToFileURL } from 'url';

const INPUT_PATH = '/root/data/wind_turbine.js';
const OUTPUT_DIR = '/root/output';
const PART_MESH_DIR = path.join(OUTPUT_DIR, 'part_meshes');
const MERGED_DIR = path.join(OUTPUT_DIR, 'merged_parts');
const EXPECTED_PATH = '/root/expected_manifest.json';

const sceneModule = await import(pathToFileURL(INPUT_PATH).href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

function buildPartMap(rootObject) {
    const partMap = new Map();

    rootObject.traverse((obj) => {
        if (obj.isGroup && obj.name) {
            partMap.set(obj.name, {
                part: obj,
                meshes: [],
            });
        }
    });

    rootObject.traverse((obj) => {
        if (!obj.isMesh) {
            return;
        }
        let current = obj.parent;
        while (current && !(current.isGroup && current.name)) {
            current = current.parent;
        }
        if (current && partMap.has(current.name)) {
            partMap.get(current.name).meshes.push(obj);
        }
    });

    return Array.from(partMap.entries())
        .map(([name, value]) => ({
            partName: name,
            meshes: value.meshes.sort((a, b) => a.name.localeCompare(b.name)),
        }))
        .filter((entry) => entry.meshes.length > 0)
        .sort((a, b) => a.partName.localeCompare(b.partName));
}

function bakeMeshGeometry(mesh) {
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

function geometryStats(geometry) {
    const position = geometry.attributes.position;
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];

    for (let index = 0; index < position.count; index += 1) {
        const x = position.getX(index);
        const y = position.getY(index);
        const z = position.getZ(index);
        min[0] = Math.min(min[0], x);
        min[1] = Math.min(min[1], y);
        min[2] = Math.min(min[2], z);
        max[0] = Math.max(max[0], x);
        max[1] = Math.max(max[1], y);
        max[2] = Math.max(max[2], z);
    }

    return {
        vertexCount: position.count,
        bbox: {
            min: min.map((value) => Number(value.toFixed(6))),
            max: max.map((value) => Number(value.toFixed(6))),
        },
    };
}

const manifest = {
    scene_file: INPUT_PATH,
    part_count: 0,
    parts: [],
};

for (const entry of buildPartMap(root)) {
    const meshEntries = [];
    const bakedGeometries = [];

    for (const mesh of entry.meshes) {
        const geometry = bakeMeshGeometry(mesh);
        const stats = geometryStats(geometry);
        meshEntries.push({
            mesh_name: mesh.name,
            obj_path: path.join(PART_MESH_DIR, entry.partName, `${mesh.name}.obj`),
            vertex_count: stats.vertexCount,
            bbox: stats.bbox,
        });
        bakedGeometries.push(geometry);
    }

    const mergedGeometry = mergeGeometries(bakedGeometries, false);
    const mergedStats = geometryStats(mergedGeometry);

    manifest.parts.push({
        part_name: entry.partName,
        mesh_count: entry.meshes.length,
        mesh_names: entry.meshes.map((mesh) => mesh.name),
        mesh_obj_paths: meshEntries.map((entry) => entry.obj_path).sort(),
        merged_obj_path: path.join(MERGED_DIR, `${entry.partName}.obj`),
        vertex_count: mergedStats.vertexCount,
        bbox: mergedStats.bbox,
        meshes: meshEntries,
    });
}

manifest.part_count = manifest.parts.length;
fs.writeFileSync(EXPECTED_PATH, `${JSON.stringify(manifest, null, 2)}\n`);
