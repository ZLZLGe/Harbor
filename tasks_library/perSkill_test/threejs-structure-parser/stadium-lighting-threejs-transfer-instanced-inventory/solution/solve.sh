#!/bin/bash
set -e

mkdir -p /root/output/rig_meshes

cat > /root/solve_lighting_inventory.mjs <<'EOF'
import fs from 'fs';
import { pathToFileURL } from 'url';
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const INPUT_PATH = '/root/data/stadium_lighting.js';
const OUTPUT_DIR = '/root/output';
const OUTPUT_JSON = `${OUTPUT_DIR}/lighting_inventory.json`;
const RIG_MESH_DIR = `${OUTPUT_DIR}/rig_meshes`;

function loadSceneModule() {
    return import(pathToFileURL(INPUT_PATH).href);
}

function roundNumber(value) {
    return Number(value.toFixed(6));
}

function roundVector(values) {
    return values.map((value) => roundNumber(value));
}

function bboxFromGeometry(geometry) {
    geometry.computeBoundingBox();
    const bbox = geometry.boundingBox;
    return {
        min: roundVector([bbox.min.x, bbox.min.y, bbox.min.z]),
        max: roundVector([bbox.max.x, bbox.max.y, bbox.max.z]),
    };
}

function unionBbox(boxes) {
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];

    for (const box of boxes) {
        for (let i = 0; i < 3; i += 1) {
            min[i] = Math.min(min[i], box.min[i]);
            max[i] = Math.max(max[i], box.max[i]);
        }
    }

    return {
        min: roundVector(min),
        max: roundVector(max),
    };
}

function makeRigidGeometry(sourceGeometry, transform) {
    let geometry = sourceGeometry.clone();
    geometry.applyMatrix4(transform);
    if (geometry.index) {
        geometry = geometry.toNonIndexed();
    }
    if (!geometry.attributes.normal) {
        geometry.computeVertexNormals();
    }
    return geometry;
}

function collectNamedRigs(root) {
    const rigs = [];
    root.traverse((object) => {
        if (object instanceof THREE.Group && object.name) {
            rigs.push(object);
        }
    });
    return rigs.sort((left, right) => left.name.localeCompare(right.name));
}

function findNearestNamedRig(object) {
    let current = object.parent;
    while (current) {
        if (current instanceof THREE.Group && current.name) {
            return current;
        }
        current = current.parent;
    }
    return null;
}

async function main() {
    const sceneModule = await loadSceneModule();
    const root = sceneModule.createScene();
    root.updateMatrixWorld(true);

    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    fs.mkdirSync(RIG_MESH_DIR, { recursive: true });

    const exporter = new OBJExporter();
    const rigs = collectNamedRigs(root);
    const rigInventory = [];
    let totalFixtureCount = 0;

    for (const rig of rigs) {
        const instancedBanks = [];
        rig.traverse((object) => {
            if (object instanceof THREE.InstancedMesh && findNearestNamedRig(object) === rig) {
                instancedBanks.push(object);
            }
        });

        instancedBanks.sort((left, right) => left.name.localeCompare(right.name));
        if (instancedBanks.length === 0) {
            continue;
        }

        const fixtureTypes = [];
        const fixtures = [];
        const rigGeometries = [];

        for (const bank of instancedBanks) {
            fixtureTypes.push({
                type_name: bank.name,
                count: bank.count,
            });

            for (let index = 0; index < bank.count; index += 1) {
                const instanceMatrix = new THREE.Matrix4();
                bank.getMatrixAt(index, instanceMatrix);
                const worldMatrix = bank.matrixWorld.clone().multiply(instanceMatrix);
                const geometry = makeRigidGeometry(bank.geometry, worldMatrix);
                const center = new THREE.Vector3().setFromMatrixPosition(worldMatrix);
                const fixtureName = `${bank.name}_${String(index).padStart(2, '0')}`;
                const bbox = bboxFromGeometry(geometry);

                fixtures.push({
                    fixture_name: fixtureName,
                    source_type: bank.name,
                    center: roundVector([center.x, center.y, center.z]),
                    bbox,
                });
                rigGeometries.push(geometry);
            }
        }

        fixtures.sort((left, right) => left.fixture_name.localeCompare(right.fixture_name));
        fixtureTypes.sort((left, right) => left.type_name.localeCompare(right.type_name));

        const mergedGeometry = mergeGeometries(rigGeometries, false);
        const mergedMesh = new THREE.Mesh(mergedGeometry);
        mergedMesh.name = rig.name;
        fs.writeFileSync(`${RIG_MESH_DIR}/${rig.name}.obj`, exporter.parse(mergedMesh));

        rigInventory.push({
            rig_name: rig.name,
            fixture_count: fixtures.length,
            fixture_types: fixtureTypes,
            merged_obj_path: `${RIG_MESH_DIR}/${rig.name}.obj`,
            bbox: unionBbox(fixtures.map((fixture) => fixture.bbox)),
            fixtures,
        });
        totalFixtureCount += fixtures.length;
    }

    const inventory = {
        scene_file: INPUT_PATH,
        rig_count: rigInventory.length,
        total_fixture_count: totalFixtureCount,
        rigs: rigInventory,
    };

    fs.writeFileSync(OUTPUT_JSON, `${JSON.stringify(inventory, null, 2)}\n`);
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
EOF

node /root/solve_lighting_inventory.mjs
