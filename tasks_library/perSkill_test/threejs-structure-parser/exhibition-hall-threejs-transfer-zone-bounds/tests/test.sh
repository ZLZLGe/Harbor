#!/bin/bash
set -e

apt-get update
apt-get install -y curl

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh

source "$HOME/.local/bin/env"

mkdir -p /logs/verifier
chmod 777 /logs/verifier

cat > /root/gen_expected_zone_report.mjs <<'EOF'
import * as THREE from 'three';
import fs from 'fs';
import { pathToFileURL } from 'url';

const INPUT_PATH = '/root/data/exhibition_hall.js';
const OUTPUT_PATH = '/root/expected_zone_report.json';

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
    const sceneModule = await import(pathToFileURL(INPUT_PATH).href);
    const root = sceneModule.createScene();
    if (!root) {
        throw new Error('createScene() must return a root object');
    }
    root.updateMatrixWorld(true);
    return root;
}

function findNearestNamedGroup(object, zoneMap) {
    let current = object.parent;
    while (current) {
        if (zoneMap.has(current.uuid)) {
            return zoneMap.get(current.uuid);
        }
        current = current.parent;
    }
    return null;
}

function buildReport(root) {
    const zoneMap = new Map();

    root.traverse((object) => {
        if (object instanceof THREE.Group && object.name) {
            zoneMap.set(object.uuid, {
                object,
                zoneName: object.name,
                parentZone: null,
                childZones: [],
                meshes: [],
            });
        }
    });

    for (const zone of zoneMap.values()) {
        const parentZone = findNearestNamedGroup(zone.object, zoneMap);
        if (parentZone) {
            zone.parentZone = parentZone.zoneName;
            parentZone.childZones.push(zone.zoneName);
        }
    }

    root.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) {
            return;
        }
        const zone = findNearestNamedGroup(object, zoneMap);
        if (zone) {
            zone.meshes.push(object);
        }
    });

    const nonEmptyZoneNames = new Set(
        [...zoneMap.values()]
            .filter((zone) => zone.meshes.length > 0)
            .map((zone) => zone.zoneName),
    );

    const zones = [...zoneMap.values()]
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
                    .filter((zoneName) => nonEmptyZoneNames.has(zoneName))
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

    return {
        scene_file: INPUT_PATH,
        zone_count: zones.length,
        zones,
    };
}

const root = await loadScene();
const report = buildReport(root);
fs.writeFileSync(OUTPUT_PATH, `${JSON.stringify(report, null, 2)}\n`);
EOF

node /root/gen_expected_zone_report.mjs

uvx \
  --with pytest==8.4.1 \
  --with pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

status=$?

mkdir -p /logs/verifier/outputs
if [ -f "/root/output/zone_bounds_report.json" ]; then
  cp /root/output/zone_bounds_report.json /logs/verifier/outputs/
fi
if [ -f "/root/expected_zone_report.json" ]; then
  cp /root/expected_zone_report.json /logs/verifier/outputs/
fi

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $status
