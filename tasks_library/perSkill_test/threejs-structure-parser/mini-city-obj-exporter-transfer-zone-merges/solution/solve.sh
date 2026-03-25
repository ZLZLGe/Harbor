#!/bin/bash
set -euo pipefail

mkdir -p /root/output/zones

cat > /root/zone_export.mjs <<'EOF'
import fs from 'fs';
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { pathToFileURL } from 'url';

const OUTPUT_DIR = '/root/output/zones';
const sceneModule = await import(pathToFileURL('/root/data/mini_city_scene.mjs').href);
const rules = JSON.parse(fs.readFileSync('/root/data/zone_rules.json', 'utf8'));
const root = sceneModule.createScene();
const fallbackByTag = rules.fallback_zone_by_semantic_tag || {};

root.updateMatrixWorld(true);

function exportZone(meshes, zoneName, exporter) {
  const worldGeometries = meshes.map((mesh) => {
    let geometry = mesh.geometry.clone();
    geometry.applyMatrix4(mesh.matrixWorld);
    if (geometry.index) {
      geometry = geometry.toNonIndexed();
    }
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }
    return geometry;
  });

  const merged = mergeGeometries(worldGeometries, false);
  const exportMesh = new THREE.Mesh(merged);
  exportMesh.name = zoneName;
  fs.writeFileSync(`${OUTPUT_DIR}/${zoneName}.obj`, exporter.parse(exportMesh));
}

const zoneBuckets = {};

root.traverse((object) => {
  if (!(object instanceof THREE.Mesh)) {
    return;
  }

  const explicitZone = typeof object.userData.zone === 'string' ? object.userData.zone.trim() : '';
  const semanticTag = typeof object.userData.semanticTag === 'string'
    ? object.userData.semanticTag.trim()
    : '';
  const zoneName = explicitZone || fallbackByTag[semanticTag];

  if (!zoneName) {
    return;
  }

  if (!zoneBuckets[zoneName]) {
    zoneBuckets[zoneName] = {
      meshes: [],
      meshNames: [],
      blocks: new Set(),
    };
  }

  zoneBuckets[zoneName].meshes.push(object);
  zoneBuckets[zoneName].meshNames.push(object.name);
  if (typeof object.userData.block === 'string' && object.userData.block.trim()) {
    zoneBuckets[zoneName].blocks.add(object.userData.block.trim());
  }
});

const exporter = new OBJExporter();
const manifest = {};

for (const zoneName of Object.keys(zoneBuckets).sort()) {
  const bucket = zoneBuckets[zoneName];
  exportZone(bucket.meshes, zoneName, exporter);
  manifest[zoneName] = {
    mesh_names: bucket.meshNames.slice().sort(),
    source_blocks: Array.from(bucket.blocks).sort(),
    mesh_count: bucket.meshes.length,
  };
}

fs.writeFileSync(
  `${OUTPUT_DIR}/zone_manifest.json`,
  `${JSON.stringify(manifest, null, 2)}\n`,
);
EOF

node /root/zone_export.mjs
