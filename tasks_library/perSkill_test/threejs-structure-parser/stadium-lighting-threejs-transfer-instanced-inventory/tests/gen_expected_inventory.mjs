import fs from 'fs';
import { pathToFileURL } from 'url';
import * as THREE from 'three';

const INPUT_PATH = '/root/data/stadium_lighting.js';
const OUTPUT_PATH = '/root/expected_inventory.json';

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

function geometryForInstance(instancedMesh, index) {
    const instanceMatrix = new THREE.Matrix4();
    instancedMesh.getMatrixAt(index, instanceMatrix);
    const worldMatrix = instancedMesh.matrixWorld.clone().multiply(instanceMatrix);
    let geometry = instancedMesh.geometry.clone();
    geometry.applyMatrix4(worldMatrix);
    if (geometry.index) {
        geometry = geometry.toNonIndexed();
    }
    return { geometry, worldMatrix };
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
    const module = await import(pathToFileURL(INPUT_PATH).href);
    const root = module.createScene();
    root.updateMatrixWorld(true);

    const rigs = [];
    root.traverse((object) => {
        if (object instanceof THREE.Group && object.name) {
            rigs.push(object);
        }
    });
    rigs.sort((left, right) => left.name.localeCompare(right.name));

    const inventory = {
        scene_file: INPUT_PATH,
        rig_count: 0,
        total_fixture_count: 0,
        rigs: [],
    };

    for (const rig of rigs) {
        const banks = [];
        rig.traverse((object) => {
            if (object instanceof THREE.InstancedMesh && findNearestNamedRig(object) === rig) {
                banks.push(object);
            }
        });
        banks.sort((left, right) => left.name.localeCompare(right.name));
        if (banks.length === 0) {
            continue;
        }

        const fixtures = [];
        const fixtureTypes = [];
        for (const bank of banks) {
            fixtureTypes.push({ type_name: bank.name, count: bank.count });
            for (let index = 0; index < bank.count; index += 1) {
                const { geometry, worldMatrix } = geometryForInstance(bank, index);
                const center = new THREE.Vector3().setFromMatrixPosition(worldMatrix);
                fixtures.push({
                    fixture_name: `${bank.name}_${String(index).padStart(2, '0')}`,
                    source_type: bank.name,
                    center: roundVector([center.x, center.y, center.z]),
                    bbox: bboxFromGeometry(geometry),
                });
            }
        }

        fixtures.sort((left, right) => left.fixture_name.localeCompare(right.fixture_name));
        fixtureTypes.sort((left, right) => left.type_name.localeCompare(right.type_name));

        inventory.rigs.push({
            rig_name: rig.name,
            fixture_count: fixtures.length,
            fixture_types: fixtureTypes,
            merged_obj_path: `/root/output/rig_meshes/${rig.name}.obj`,
            bbox: unionBbox(fixtures.map((fixture) => fixture.bbox)),
            fixtures,
        });
        inventory.total_fixture_count += fixtures.length;
    }

    inventory.rig_count = inventory.rigs.length;
    fs.writeFileSync(OUTPUT_PATH, `${JSON.stringify(inventory, null, 2)}\n`);
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
