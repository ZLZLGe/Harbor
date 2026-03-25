import json
import math
import subprocess
from pathlib import Path

import pytest


OUTPUT_ROOT = Path("/root/output/zones")
MANIFEST_PATH = OUTPUT_ROOT / "zone_manifest.json"
EXPECTED_ZONES = {
    "building_shells",
    "pedestrian_paths",
    "retail_frontage",
    "street_furniture",
}


def round6(value):
    return round(float(value), 6)


def parse_obj_metrics(path: Path):
    raw_vertices = []
    face_count = 0

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z, *rest = line.strip().split()
                raw_vertices.append((round6(x), round6(y), round6(z)))
            elif line.startswith("f "):
                face_count += 1

    assert raw_vertices, f"No vertices found in {path}"

    unique_vertices = sorted(set(raw_vertices))
    xs = [vertex[0] for vertex in unique_vertices]
    ys = [vertex[1] for vertex in unique_vertices]
    zs = [vertex[2] for vertex in unique_vertices]

    return {
        "face_count": face_count,
        "unique_vertex_count": len(unique_vertices),
        "centroid": (
            round6(sum(xs) / len(unique_vertices)),
            round6(sum(ys) / len(unique_vertices)),
            round6(sum(zs) / len(unique_vertices)),
        ),
        "bbox_min": (min(xs), min(ys), min(zs)),
        "bbox_max": (max(xs), max(ys), max(zs)),
        "signature": round6(
            sum((x * 0.11) + (y * 0.17) + (z * 0.23) for x, y, z in unique_vertices)
        ),
    }


def assert_metrics_close(actual, expected):
    assert actual["face_count"] == expected["face_count"]
    assert actual["unique_vertex_count"] == expected["unique_vertex_count"]

    for key in ("centroid", "bbox_min", "bbox_max"):
        for actual_value, expected_value in zip(actual[key], expected[key]):
            assert math.isclose(actual_value, expected_value, abs_tol=1e-5), (
                f"{key} mismatch: actual={actual[key]} expected={expected[key]}"
            )

    assert math.isclose(actual["signature"], expected["signature"], abs_tol=1e-5)


@pytest.fixture(scope="session")
def expected_payload():
    script = """
import fs from 'fs';
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { createScene } from '/root/data/mini_city_scene.mjs';

const rules = JSON.parse(fs.readFileSync('/root/data/zone_rules.json', 'utf8'));
const root = createScene();
const fallbackByTag = rules.fallback_zone_by_semantic_tag || {};

function round6(value) {
    return Number(value.toFixed(6));
}

function metricsFromGeometry(inputGeometry) {
    let geometry = inputGeometry.clone();
    if (geometry.index) {
        geometry = geometry.toNonIndexed();
    }

    const position = geometry.getAttribute('position');
    const seen = new Set();
    const vertices = [];

    for (let index = 0; index < position.count; index += 1) {
        const vertex = [
            round6(position.getX(index)),
            round6(position.getY(index)),
            round6(position.getZ(index)),
        ];
        const key = vertex.join(',');
        if (!seen.has(key)) {
            seen.add(key);
            vertices.push(vertex);
        }
    }

    vertices.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);

    const xs = vertices.map((vertex) => vertex[0]);
    const ys = vertices.map((vertex) => vertex[1]);
    const zs = vertices.map((vertex) => vertex[2]);

    return {
        face_count: position.count / 3,
        unique_vertex_count: vertices.length,
        centroid: [
            round6(xs.reduce((sum, value) => sum + value, 0) / vertices.length),
            round6(ys.reduce((sum, value) => sum + value, 0) / vertices.length),
            round6(zs.reduce((sum, value) => sum + value, 0) / vertices.length),
        ],
        bbox_min: [Math.min(...xs), Math.min(...ys), Math.min(...zs)],
        bbox_max: [Math.max(...xs), Math.max(...ys), Math.max(...zs)],
        signature: round6(vertices.reduce(
            (sum, [x, y, z]) => sum + (x * 0.11) + (y * 0.17) + (z * 0.23),
            0,
        )),
    };
}

root.updateMatrixWorld(true);

const payload = {};

root.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) {
        return;
    }

    const explicitZone = typeof object.userData.zone === 'string'
        ? object.userData.zone.trim()
        : '';
    const semanticTag = typeof object.userData.semanticTag === 'string'
        ? object.userData.semanticTag.trim()
        : '';
    const zoneName = explicitZone || fallbackByTag[semanticTag];

    if (!zoneName) {
        return;
    }

    if (!payload[zoneName]) {
        payload[zoneName] = {
            mesh_names: [],
            source_blocks: new Set(),
            geometries: [],
        };
    }

    let geometry = object.geometry.clone();
    geometry.applyMatrix4(object.matrixWorld);

    payload[zoneName].mesh_names.push(object.name);
    if (typeof object.userData.block === 'string' && object.userData.block.trim()) {
        payload[zoneName].source_blocks.add(object.userData.block.trim());
    }
    payload[zoneName].geometries.push(geometry);
});

for (const zoneName of Object.keys(payload)) {
    const entry = payload[zoneName];
    const merged = mergeGeometries(entry.geometries, false);
    payload[zoneName] = {
        mesh_names: entry.mesh_names.sort(),
        source_blocks: Array.from(entry.source_blocks).sort(),
        mesh_count: entry.mesh_names.length,
        metrics: metricsFromGeometry(merged),
    };
}

process.stdout.write(JSON.stringify(payload));
"""

    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


@pytest.fixture(scope="session")
def actual_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_zone_output_directory_and_manifest_exist():
    assert OUTPUT_ROOT.is_dir(), f"Missing zone output directory: {OUTPUT_ROOT}"
    assert MANIFEST_PATH.is_file(), f"Missing zone manifest: {MANIFEST_PATH}"


def test_expected_zone_obj_files_exist(expected_payload):
    actual_zone_files = {path.stem for path in OUTPUT_ROOT.glob("*.obj")}
    assert actual_zone_files == EXPECTED_ZONES
    assert set(expected_payload.keys()) == EXPECTED_ZONES
    assert (OUTPUT_ROOT / "pedestrian_paths.obj").is_file()


def test_manifest_matches_expected_assignments(expected_payload, actual_manifest):
    assert set(actual_manifest.keys()) == EXPECTED_ZONES

    for zone_name, expected in expected_payload.items():
        actual = actual_manifest[zone_name]
        assert actual["mesh_count"] == expected["mesh_count"]
        assert sorted(actual["mesh_names"]) == expected["mesh_names"]
        assert sorted(actual["source_blocks"]) == expected["source_blocks"]


def test_zone_obj_geometry_matches_expected(expected_payload):
    for zone_name, expected in expected_payload.items():
        actual = parse_obj_metrics(OUTPUT_ROOT / f"{zone_name}.obj")
        assert_metrics_close(actual, expected["metrics"])


def test_pedestrian_paths_spans_multiple_blocks(actual_manifest):
    assert sorted(actual_manifest["pedestrian_paths"]["source_blocks"]) == [
        "market_corner",
        "north_gateway",
        "plaza_arcade",
        "south_transit",
    ]
