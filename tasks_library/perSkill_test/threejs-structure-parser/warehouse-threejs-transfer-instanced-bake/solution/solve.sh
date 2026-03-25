#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/bake_warehouse_scene.mjs <<'EOF'
import fs from 'fs';
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { pathToFileURL } from 'url';

const INPUT_PATH = '/root/data/warehouse_scene.js';
const OUTPUT_DIR = '/root/output';
const OUTPUT_OBJ = `${OUTPUT_DIR}/baked_scene.obj`;
const OUTPUT_REPORT = `${OUTPUT_DIR}/instance_report.json`;

function bakeGeometry(geometry, matrix) {
    let baked = geometry.clone();
    baked.applyMatrix4(matrix);
    if (baked.index) {
        baked = baked.toNonIndexed();
    }
    if (!baked.attributes.normal) {
        baked.computeVertexNormals();
    }
    return baked;
}

async function main() {
    const sceneModule = await import(pathToFileURL(INPUT_PATH).href);
    const root = sceneModule.createScene();
    root.updateMatrixWorld(true);

    const geometries = [];
    const instancedNodes = [];
    let regularMeshCount = 0;
    const instanceMatrix = new THREE.Matrix4();
    const worldMatrix = new THREE.Matrix4();

    root.traverse((object) => {
        if (object.isInstancedMesh) {
            instancedNodes.push({
                node_name: object.name || `instanced_${instancedNodes.length}`,
                instance_count: object.count,
            });

            for (let i = 0; i < object.count; i += 1) {
                object.getMatrixAt(i, instanceMatrix);
                worldMatrix.copy(object.matrixWorld).multiply(instanceMatrix);
                geometries.push(bakeGeometry(object.geometry, worldMatrix));
            }
            return;
        }

        if (object.isMesh) {
            regularMeshCount += 1;
            geometries.push(bakeGeometry(object.geometry, object.matrixWorld));
        }
    });

    const merged = mergeGeometries(geometries, false);
    const bakedMesh = new THREE.Mesh(merged);
    bakedMesh.name = 'baked_scene';

    const exporter = new OBJExporter();
    fs.writeFileSync(OUTPUT_OBJ, exporter.parse(bakedMesh));

    instancedNodes.sort((a, b) => a.node_name.localeCompare(b.node_name));
    const totalInstances = instancedNodes.reduce(
        (sum, entry) => sum + entry.instance_count,
        0,
    );

    const report = {
        scene_file: 'warehouse_scene.js',
        merged_obj: 'baked_scene.obj',
        instanced_nodes: instancedNodes,
        total_instances: totalInstances,
        total_baked_primitives: regularMeshCount + totalInstances,
    };
    fs.writeFileSync(OUTPUT_REPORT, `${JSON.stringify(report, null, 2)}\n`);
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
EOF

node /root/bake_warehouse_scene.mjs
