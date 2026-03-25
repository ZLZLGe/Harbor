import json
import os
import subprocess

import numpy as np
import pytest


OBJ_PATH = "/root/output/wayfinding_sign.obj"
REQUIRED_OBJECTS = {
  "panel_blank",
  "back_strap",
  "left_post",
  "right_post",
  "left_finial",
  "right_finial",
}
ROUND_DECIMALS = 5
TOLERANCE = 1e-5

EXPECTED_METRICS_SCRIPT = r"""
import * as THREE from 'three';
import { pathToFileURL } from 'url';

const moduleUrl = pathToFileURL('/root/data/wayfinding_scene.js').href;
const sceneModule = await import(moduleUrl);
const root = sceneModule.buildWayfindingSignScene();
root.updateMatrixWorld(true);

const zUpMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
const objects = {};

function bakeMesh(mesh) {
  const baked = mesh.geometry.clone();
  baked.applyMatrix4(mesh.matrixWorld);
  baked.applyMatrix4(zUpMatrix);
  return baked;
}

function collectVertices(geometry) {
  const position = geometry.getAttribute('position');
  const vertices = [];
  for (let index = 0; index < position.count; index += 1) {
    vertices.push([
      position.getX(index),
      position.getY(index),
      position.getZ(index),
    ]);
  }
  return vertices;
}

root.traverse((obj) => {
  if (!obj.isMesh) {
    return;
  }
  const baked = bakeMesh(obj);
  objects[obj.name] = {
    vertices: collectVertices(baked),
  };
});

const panel = root.getObjectByName('panel_blank');
const panelBaked = bakeMesh(panel);
const panelVertices = objects.panel_blank.vertices;
const panelYs = panelVertices.map((vertex) => vertex[1]);

const holeAngles = [0, Math.PI / 2, Math.PI, Math.PI * 1.5];
const holeSamples = [];
for (const [centerX, centerY] of panel.userData.mountingHoleCenters) {
  for (const angle of holeAngles) {
    for (const localZ of [-panel.userData.panelThickness / 2, panel.userData.panelThickness / 2]) {
      const point = new THREE.Vector3(
        centerX + Math.cos(angle) * panel.userData.mountingHoleRadius,
        centerY + Math.sin(angle) * panel.userData.mountingHoleRadius,
        localZ,
      );
      point.applyMatrix4(panel.matrixWorld);
      point.applyMatrix4(zUpMatrix);
      holeSamples.push([point.x, point.y, point.z]);
    }
  }
}

function lexicographicSample(vertices, count) {
  const seen = new Set();
  const unique = [];
  for (const vertex of vertices) {
    const rounded = vertex.map((value) => value.toFixed(6)).join(',');
    if (!seen.has(rounded)) {
      seen.add(rounded);
      unique.push(vertex);
    }
  }
  unique.sort((left, right) => {
    for (let axis = 0; axis < 3; axis += 1) {
      if (left[axis] !== right[axis]) {
        return left[axis] - right[axis];
      }
    }
    return 0;
  });
  return unique.slice(0, count);
}

function computeBounds(vertices) {
  const mins = [Infinity, Infinity, Infinity];
  const maxs = [-Infinity, -Infinity, -Infinity];
  for (const vertex of vertices) {
    for (let axis = 0; axis < 3; axis += 1) {
      mins[axis] = Math.min(mins[axis], vertex[axis]);
      maxs[axis] = Math.max(maxs[axis], vertex[axis]);
    }
  }
  return { min: mins, max: maxs };
}

console.log(JSON.stringify({
  panelThickness: Math.max(...panelYs) - Math.min(...panelYs),
  panelBounds: computeBounds(panelVertices),
  holeSamples,
  finialSamples: {
    left_finial: lexicographicSample(objects.left_finial.vertices, 8),
    right_finial: lexicographicSample(objects.right_finial.vertices, 8),
  },
}));
"""


def parse_obj_objects(path):
  objects = {}
  current_name = None

  with open(path, "r", encoding="utf-8") as handle:
    for raw_line in handle:
      line = raw_line.strip()
      if not line:
        continue
      if line.startswith("o "):
        current_name = line[2:].strip()
        objects[current_name] = {
          "vertices": [],
          "faces": 0,
        }
      elif line.startswith("v "):
        assert current_name is not None, "OBJ vertex appeared before any object record"
        _, x, y, z = line.split()[:4]
        objects[current_name]["vertices"].append([float(x), float(y), float(z)])
      elif line.startswith("f "):
        assert current_name is not None, "OBJ face appeared before any object record"
        objects[current_name]["faces"] += 1

  return objects


def rounded_point_set(vertices):
  rounded = np.round(np.asarray(vertices, dtype=float), ROUND_DECIMALS)
  return {tuple(point.tolist()) for point in rounded}


def compute_bounds(vertices):
  array = np.asarray(vertices, dtype=float)
  return array.min(axis=0), array.max(axis=0)


@pytest.fixture(scope="module")
def parsed_output():
  assert os.path.exists(OBJ_PATH), f"missing output file: {OBJ_PATH}"
  assert os.path.getsize(OBJ_PATH) > 0, "output OBJ is empty"
  return parse_obj_objects(OBJ_PATH)


@pytest.fixture(scope="module")
def expected_metrics():
  result = subprocess.run(
    ["node", "--input-type=module", "-e", EXPECTED_METRICS_SCRIPT],
    check=True,
    capture_output=True,
    text=True,
  )
  return json.loads(result.stdout)


def test_required_objects_exist_and_have_faces(parsed_output):
  assert set(parsed_output) == REQUIRED_OBJECTS, (
    f"expected OBJ objects {sorted(REQUIRED_OBJECTS)}, got {sorted(parsed_output)}"
  )
  for name, payload in parsed_output.items():
    assert payload["vertices"], f"{name} does not contain any vertices"
    assert payload["faces"] > 0, f"{name} does not contain any faces"


def test_panel_thickness_matches_expected(parsed_output, expected_metrics):
  panel_vertices = np.asarray(parsed_output["panel_blank"]["vertices"], dtype=float)
  actual_thickness = panel_vertices[:, 1].max() - panel_vertices[:, 1].min()
  assert np.isclose(actual_thickness, expected_metrics["panelThickness"], atol=TOLERANCE), (
    f"panel thickness mismatch: expected {expected_metrics['panelThickness']}, "
    f"got {actual_thickness}"
  )


def test_panel_bounds_match_z_up_orientation(parsed_output, expected_metrics):
  actual_min, actual_max = compute_bounds(parsed_output["panel_blank"]["vertices"])
  expected_min = np.asarray(expected_metrics["panelBounds"]["min"], dtype=float)
  expected_max = np.asarray(expected_metrics["panelBounds"]["max"], dtype=float)

  assert np.allclose(actual_min, expected_min, atol=TOLERANCE), (
    f"panel bbox min mismatch: expected {expected_min.tolist()}, got {actual_min.tolist()}"
  )
  assert np.allclose(actual_max, expected_max, atol=TOLERANCE), (
    f"panel bbox max mismatch: expected {expected_max.tolist()}, got {actual_max.tolist()}"
  )


def test_mounting_hole_rim_samples_are_preserved(parsed_output, expected_metrics):
  panel_points = rounded_point_set(parsed_output["panel_blank"]["vertices"])
  for sample in expected_metrics["holeSamples"]:
    rounded = tuple(np.round(np.asarray(sample, dtype=float), ROUND_DECIMALS).tolist())
    assert rounded in panel_points, f"panel mounting hole sample missing from OBJ: {sample}"


def test_finials_keep_lathe_profile_samples(parsed_output, expected_metrics):
  for finial_name, samples in expected_metrics["finialSamples"].items():
    actual_points = rounded_point_set(parsed_output[finial_name]["vertices"])
    for sample in samples:
      rounded = tuple(np.round(np.asarray(sample, dtype=float), ROUND_DECIMALS).tolist())
      assert rounded in actual_points, (
        f"{finial_name} is missing expected profile sample {sample}"
      )
