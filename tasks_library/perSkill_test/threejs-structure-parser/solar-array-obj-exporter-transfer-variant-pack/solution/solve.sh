#!/bin/bash
set -euo pipefail

mkdir -p /root/output/variants

cat > /root/export_solar_variants.mjs <<'EOF'
import * as THREE from 'three';
import fs from 'fs';
import { pathToFileURL } from 'url';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const DATA_PATH = '/root/data/object.js';
const OUTPUT_ROOT = '/root/output/variants';

function cloneWorldGeometry(mesh) {
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

function collectMeshes(root) {
    const meshes = [];
    root.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
            meshes.push(obj);
        }
    });
    return meshes;
}

function exportMesh(exporter, mesh, destination, nameOverride) {
    const geometry = cloneWorldGeometry(mesh);
    const exportMeshObject = new THREE.Mesh(geometry);
    exportMeshObject.name = nameOverride ?? mesh.name ?? 'mesh';
    fs.writeFileSync(destination, exporter.parse(exportMeshObject));
}

async function main() {
    const moduleUrl = pathToFileURL(DATA_PATH).href;
    const sceneModule = await import(moduleUrl);
    const exporter = new OBJExporter();

    for (const variantName of sceneModule.VARIANT_NAMES) {
        const root = sceneModule.createVariantScene(variantName);
        root.updateMatrixWorld(true);

        const panelField = root.getObjectByName('panel_field');
        const rackAssembly = root.getObjectByName('rack_assembly');

        if (!panelField || !rackAssembly) {
            throw new Error(`Variant ${variantName} is missing panel_field or rack_assembly`);
        }

        const variantDir = `${OUTPUT_ROOT}/${variantName}`;
        const panelDir = `${variantDir}/panels`;
        fs.mkdirSync(panelDir, { recursive: true });

        let unnamedPanelIndex = 0;
        for (const mesh of collectMeshes(panelField)) {
            const meshName = mesh.name || `unnamed_panel_${unnamedPanelIndex++}`;
            exportMesh(exporter, mesh, `${panelDir}/${meshName}.obj`, meshName);
        }

        const rackMeshes = collectMeshes(rackAssembly);
        if (rackMeshes.length === 0) {
            throw new Error(`Variant ${variantName} has no rack meshes`);
        }

        const rackObject = new THREE.Mesh(
            mergeGeometries(rackMeshes.map((mesh) => cloneWorldGeometry(mesh)), false),
        );
        rackObject.name = `${variantName}_rack`;
        fs.writeFileSync(`${variantDir}/rack.obj`, exporter.parse(rackObject));
    }
}

main().catch((error) => {
    console.error('Solar variant export failed:', error);
    process.exit(1);
});
EOF

node /root/export_solar_variants.mjs
