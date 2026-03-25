import json
import math
import subprocess
from collections import Counter
from pathlib import Path

import pytest


OUTPUT_ROOT = Path("/root/output/variants")
MANIFEST_PATH = OUTPUT_ROOT / "variant_manifest.json"
SPEC_PATH = Path("/root/data/bracket_specs.json")
PRIMARY_OUTPUT = OUTPUT_ROOT / "brace_double_slot.obj"


def round6(value):
    return round(float(value), 6)


def parse_obj_metrics(path: Path):
    vertices = []
    face_count = 0

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z, *rest = line.strip().split()
                vertices.append((round6(x), round6(y), round6(z)))
            elif line.startswith("f "):
                face_count += 1

    assert vertices, f"No vertices found in {path}"

    unique_vertices = sorted(set(vertices))
    xs = [vertex[0] for vertex in unique_vertices]
    ys = [vertex[1] for vertex in unique_vertices]
    zs = [vertex[2] for vertex in unique_vertices]

    return {
        "face_count": face_count,
        "unique_vertex_count": len(unique_vertices),
        "bbox_min": (min(xs), min(ys), min(zs)),
        "bbox_max": (max(xs), max(ys), max(zs)),
        "centroid": (
            round6(sum(xs) / len(xs)),
            round6(sum(ys) / len(ys)),
            round6(sum(zs) / len(zs)),
        ),
        "signature": round6(
            sum((x * 0.09) + (y * 0.13) + (z * 0.17) for x, y, z in unique_vertices)
        ),
    }


def assert_metrics_close(actual, expected):
    assert actual["face_count"] == expected["face_count"]
    assert actual["unique_vertex_count"] == expected["unique_vertex_count"]

    for key in ("bbox_min", "bbox_max", "centroid"):
        for actual_value, expected_value in zip(actual[key], expected[key]):
            assert math.isclose(actual_value, expected_value, abs_tol=1e-5), (
                f"{key} mismatch: actual={actual[key]} expected={expected[key]}"
            )

    assert math.isclose(actual["signature"], expected["signature"], abs_tol=1e-5)


@pytest.fixture(scope="session")
def spec_document():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def expected_payload():
    script = """
import fs from 'fs';
import * as THREE from 'three';
import { buildBracketKit, buildBracketVariant } from '/root/data/bracket_factory.mjs';

const specDocument = JSON.parse(fs.readFileSync('/root/data/bracket_specs.json', 'utf8'));

function round6(value) {
  return Number(value.toFixed(6));
}

function metricsForObject(object3D) {
  object3D.updateMatrixWorld(true);

  const unique = new Set();
  const vertices = [];
  let faceCount = 0;

  object3D.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) {
      return;
    }

    let geometry = child.geometry.clone();
    geometry.applyMatrix4(child.matrixWorld);
    if (geometry.index) {
      geometry = geometry.toNonIndexed();
    }

    const position = geometry.getAttribute('position');
    faceCount += position.count / 3;

    for (let i = 0; i < position.count; i += 1) {
      const vertex = [
        round6(position.getX(i)),
        round6(position.getY(i)),
        round6(position.getZ(i)),
      ];
      const key = vertex.join(',');
      if (!unique.has(key)) {
        unique.add(key);
        vertices.push(vertex);
      }
    }
  });

  vertices.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);

  const xs = vertices.map((vertex) => vertex[0]);
  const ys = vertices.map((vertex) => vertex[1]);
  const zs = vertices.map((vertex) => vertex[2]);

  return {
    face_count: faceCount,
    unique_vertex_count: vertices.length,
    bbox_min: [Math.min(...xs), Math.min(...ys), Math.min(...zs)],
    bbox_max: [Math.max(...xs), Math.max(...ys), Math.max(...zs)],
    centroid: [
      round6(xs.reduce((sum, value) => sum + value, 0) / xs.length),
      round6(ys.reduce((sum, value) => sum + value, 0) / ys.length),
      round6(zs.reduce((sum, value) => sum + value, 0) / zs.length),
    ],
    signature: round6(vertices.reduce(
      (sum, [x, y, z]) => sum + (x * 0.09) + (y * 0.13) + (z * 0.17),
      0,
    )),
  };
}

const payload = {
  manifest: {
    kit_name: specDocument.kit_name,
    overview_file: specDocument.overview_file,
    variant_names: specDocument.variants.map((variant) => variant.name),
    variants: {},
  },
  variant_metrics: {},
};

for (const variant of specDocument.variants) {
  payload.manifest.variants[variant.name] = {
    component_count: variant.components.length,
    component_names: variant.components.map((component) => component.name),
    kit_offset: variant.kit_offset,
  };

  const group = buildBracketVariant(variant);
  payload.variant_metrics[variant.name] = metricsForObject(group);
}

payload.overview_metrics = metricsForObject(buildBracketKit(specDocument));

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


def test_output_directory_and_required_files_exist(spec_document):
    assert OUTPUT_ROOT.is_dir(), f"Missing output directory: {OUTPUT_ROOT}"

    expected_obj_files = {f"{variant['name']}.obj" for variant in spec_document["variants"]}
    expected_obj_files.add(spec_document["overview_file"])

    actual_obj_files = {path.name for path in OUTPUT_ROOT.glob("*.obj")}
    assert actual_obj_files == expected_obj_files
    assert PRIMARY_OUTPUT.is_file()
    assert MANIFEST_PATH.is_file()


def test_manifest_matches_spec_contract(expected_payload, actual_manifest):
    expected_manifest = expected_payload["manifest"]

    assert actual_manifest["kit_name"] == expected_manifest["kit_name"]
    assert actual_manifest["overview_file"] == expected_manifest["overview_file"]
    assert Counter(actual_manifest["variant_names"]) == Counter(
        expected_manifest["variant_names"]
    )
    assert set(actual_manifest["variants"]) == set(expected_manifest["variants"])

    for variant_name, expected_variant in expected_manifest["variants"].items():
        actual_variant = actual_manifest["variants"][variant_name]
        assert actual_variant["component_count"] == expected_variant["component_count"]
        assert Counter(actual_variant["component_names"]) == Counter(
            expected_variant["component_names"]
        )
        assert actual_variant["kit_offset"] == expected_variant["kit_offset"]


def test_each_variant_obj_matches_expected_geometry(expected_payload, spec_document):
    for variant in spec_document["variants"]:
        variant_name = variant["name"]
        actual = parse_obj_metrics(OUTPUT_ROOT / f"{variant_name}.obj")
        expected = expected_payload["variant_metrics"][variant_name]
        assert_metrics_close(actual, expected)


def test_overview_obj_matches_expected_geometry(expected_payload, spec_document):
    actual = parse_obj_metrics(OUTPUT_ROOT / spec_document["overview_file"])
    assert_metrics_close(actual, expected_payload["overview_metrics"])


def test_manifest_variant_names_match_variant_entries(actual_manifest):
    assert Counter(actual_manifest["variant_names"]) == Counter(
        actual_manifest["variants"].keys()
    )
