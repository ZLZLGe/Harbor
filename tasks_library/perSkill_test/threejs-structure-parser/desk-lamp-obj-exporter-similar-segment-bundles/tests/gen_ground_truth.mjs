import * as THREE from 'three';
import fs from 'fs';
import { pathToFileURL } from 'url';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

const INPUT_PATH = '/root/data/object.js';
const GROUND_TRUTH_DIR = '/root/ground_truth';
const PART_MESH_DIR = `${GROUND_TRUTH_DIR}/part_meshes`;
const LINK_DIR = `${GROUND_TRUTH_DIR}/links`;

function collectSegments(root) {
    const segmentMap = {};

    root.traverse((obj) => {
        if (obj instanceof THREE.Group && obj.name) {
            segmentMap[obj.name] = { meshes: [] };
        }
    });

    root.traverse((obj) => {
        if (!(obj instanceof THREE.Mesh)) {
            return;
        }

        let current = obj.parent;
        while (current && !(current instanceof THREE.Group && current.name)) {
            current = current.parent;
        }

        if (current && segmentMap[current.name]) {
            segmentMap[current.name].meshes.push(obj);
        }
    });

    return Object.fromEntries(
        Object.entries(segmentMap).filter(([, value]) => value.meshes.length > 0),
    );
}

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

async function main() {
    const moduleUrl = pathToFileURL(INPUT_PATH).href;
    const sceneModule = await import(moduleUrl);
    const root = typeof sceneModule.createScene === 'function'
        ? sceneModule.createScene()
        : sceneModule.sceneObject;

    root.updateMatrixWorld(true);

    fs.mkdirSync(PART_MESH_DIR, { recursive: true });
    fs.mkdirSync(LINK_DIR, { recursive: true });

    const exporter = new OBJExporter();
    const segments = collectSegments(root);
    let unnamedIndex = 0;

    for (const [segmentName, data] of Object.entries(segments)) {
        const segmentDir = `${PART_MESH_DIR}/${segmentName}`;
        fs.mkdirSync(segmentDir, { recursive: true });

        const mergedGeometries = [];

        for (const mesh of data.meshes) {
            const geometry = cloneWorldGeometry(mesh);
            mergedGeometries.push(geometry);

            const exportMesh = new THREE.Mesh(geometry);
            const meshName = mesh.name || `unnamed_mesh_${unnamedIndex++}`;
            exportMesh.name = meshName;
            fs.writeFileSync(
                `${segmentDir}/${meshName}.obj`,
                exporter.parse(exportMesh),
            );
        }

        const merged = mergeGeometries(mergedGeometries, false);
        const mergedMesh = new THREE.Mesh(merged);
        mergedMesh.name = segmentName;
        fs.writeFileSync(`${LINK_DIR}/${segmentName}.obj`, exporter.parse(mergedMesh));
    }
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
