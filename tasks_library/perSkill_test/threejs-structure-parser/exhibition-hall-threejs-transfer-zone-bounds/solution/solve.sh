#!/bin/bash
set -euo pipefail

mkdir -p /root/output

cat > /root/solve_zone_bounds.mjs <<'EOF'
import * as THREE from 'three';
import fs from 'fs';
import { pathToFileURL } from 'url';

const INPUT_PATH = '/root/data/exhibition_hall.js';
const OUTPUT_PATH = '/root/output/zone_bounds_report.json';

function roundNumber(value) {
    return Number(value.toFixed(6));
}

function toVectorArray(vector) {
    return [roundNumber(vector.x), roundNumber(vector.y), roundNumber(vector.z)];
}

function meshWorldBox(mesh) {
    const geometry = mesh.geometry.clone();
    geometry.applyMatrix4(mesh.matrixWorld);
    geometry.computeBoundingBox();
    return geometry.boundingBox.clone();
}

async function loadScene() {
    const moduleUrl = pathToFileURL(INPUT_PATH).href;
    const sceneModule = await import(moduleUrl);
    const root = sceneModule.createScene();
    if (!root) {
        throw new Error('createScene() must return a root object');
    }
    root.updateMatrixWorld(true);
    return root;
}

function collectZones(root) {
    const zones = new Map();

    root.traverse((object) => {
        if (object instanceof THREE.Group && object.name) {
            zones.set(object.uuid, {
                object,
                zoneName: object.name,
                parentZone: null,
                childZones: [],
                meshes: [],
            });
        }
    });

    for (const zone of zones.values()) {
        let parent = zone.object.parent;
        while (parent) {
            const parentZone = zones.get(parent.uuid);
            if (parentZone) {
                zone.parentZone = parentZone.zoneName;
                parentZone.childZones.push(zone.zoneName);
                break;
            }
            parent = parent.parent;
        }
    }

    root.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) {
            return;
        }

        let parent = object.parent;
        while (parent) {
            const zone = zones.get(parent.uuid);
            if (zone) {
                zone.meshes.push(object);
                return;
            }
            parent = parent.parent;
        }
    });

    return [...zones.values()]
        .filter((zone) => zone.meshes.length > 0)
        .map((zone) => {
            const bbox = new THREE.Box3();
            for (const mesh of zone.meshes) {
                bbox.union(meshWorldBox(mesh));
            }
            return {
                zone_name: zone.zoneName,
                parent_zone: zone.parentZone,
                child_zones: zone.childZones
                    .filter((childZoneName) => zonesHasMeshes(zones, childZoneName))
                    .sort(),
                mesh_count: zone.meshes.length,
                direct_mesh_names: zone.meshes.map((mesh) => mesh.name).sort(),
                world_bbox: {
                    min: toVectorArray(bbox.min),
                    max: toVectorArray(bbox.max),
                },
            };
        })
        .sort((left, right) => left.zone_name.localeCompare(right.zone_name));
}

function zonesHasMeshes(zones, zoneName) {
    for (const zone of zones.values()) {
        if (zone.zoneName === zoneName) {
            return zone.meshes.length > 0;
        }
    }
    return false;
}

async function main() {
    const root = await loadScene();
    const zones = collectZones(root);
    const report = {
        scene_file: INPUT_PATH,
        zone_count: zones.length,
        zones,
    };
    fs.writeFileSync(OUTPUT_PATH, `${JSON.stringify(report, null, 2)}\n`);
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
EOF

node /root/solve_zone_bounds.mjs
