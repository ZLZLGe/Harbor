import json
import subprocess
from pathlib import Path

import numpy as np


OUTPUT_DIR = Path("/root/output")
MANIFEST_PATH = OUTPUT_DIR / "floor_manifest.json"
FLOOR_DIR = OUTPUT_DIR / "floors"


def parse_obj_vertices(file_path: Path) -> np.ndarray:
    vertices = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z, *_ = line.strip().split()
                vertices.append([float(x), float(y), float(z)])
    return np.asarray(vertices, dtype=np.float64)


def canonicalize_vertices(vertices: np.ndarray) -> np.ndarray:
    if len(vertices) == 0:
        return vertices.reshape(0, 3)
    rounded = np.round(vertices, decimals=6)
    unique = np.unique(rounded, axis=0)
    order = np.lexsort((unique[:, 2], unique[:, 1], unique[:, 0]))
    return unique[order]


def load_expected() -> dict:
    script = r"""
import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { pathToFileURL } from 'url';

const sceneModule = await import(pathToFileURL('/root/data/atrium_scene.js').href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

const exporter = new OBJExporter();
const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
const floorMap = new Map();

root.traverse((object) => {
  if (object.isGroup && object.name) {
    floorMap.set(object.name, object);
  }
});

function findParentFloor(floorObject) {
  let parent = floorObject.parent;
  while (parent) {
    if (parent.isGroup && parent.name && floorMap.has(parent.name)) {
      return parent.name;
    }
    parent = parent.parent;
  }
  return null;
}

function collectOwnedMeshes(floorObject) {
  const meshes = [];

  const visit = (object) => {
    if (object !== floorObject && object.isGroup && object.name && floorMap.has(object.name)) {
      return;
    }
    if (object.isMesh) {
      meshes.push(object);
    }
    for (const child of object.children) {
      visit(child);
    }
  };

  visit(floorObject);
  return meshes;
}

function bakeGeometry(mesh) {
  let geometry = mesh.geometry.clone();
  geometry.applyMatrix4(mesh.matrixWorld);
  geometry.applyMatrix4(axisMatrix);
  if (geometry.index) {
    geometry = geometry.toNonIndexed();
  }
  if (!geometry.attributes.normal) {
    geometry.computeVertexNormals();
  }
  return geometry;
}

function exportVertices(meshes) {
  const merged = mergeGeometries(meshes.map(bakeGeometry), false);
  const objText = exporter.parse(new THREE.Mesh(merged));
  const vertices = [];
  for (const line of objText.split('\n')) {
    if (!line.startsWith('v ')) {
      continue;
    }
    const [, x, y, z] = line.trim().split(/\s+/);
    vertices.push([
      Number(Number(x).toFixed(6)),
      Number(Number(y).toFixed(6)),
      Number(Number(z).toFixed(6)),
    ]);
  }
  return vertices;
}

const floors = [];
for (const floorName of Array.from(floorMap.keys()).sort()) {
  const floorObject = floorMap.get(floorName);
  const ownedMeshes = collectOwnedMeshes(floorObject);
  if (ownedMeshes.length === 0) {
    continue;
  }
  floors.push({
    floor_name: floorName,
    parent_floor: findParentFloor(floorObject),
    mesh_count: ownedMeshes.length,
    merged_obj_file: `floors/${floorName}.obj`,
    vertices: exportVertices(ownedMeshes),
  });
}

console.log(JSON.stringify({
  scene_file: 'atrium_scene.js',
  axis_conversion: 'Y-up to Z-up',
  floors,
}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        cwd="/root",
    )
    return json.loads(completed.stdout)


EXPECTED = load_expected()


def expected_manifest_contract():
    return {
        "scene_file": EXPECTED["scene_file"],
        "axis_conversion": EXPECTED["axis_conversion"],
        "floors": [
            {
                "floor_name": item["floor_name"],
                "parent_floor": item["parent_floor"],
                "mesh_count": item["mesh_count"],
                "merged_obj_file": item["merged_obj_file"],
            }
            for item in EXPECTED["floors"]
        ],
    }


def test_required_outputs_exist():
    assert MANIFEST_PATH.exists(), "缺少 /root/output/floor_manifest.json"
    assert FLOOR_DIR.is_dir(), "缺少 /root/output/floors"


def test_manifest_matches_contract():
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    assert manifest["scene_file"] == "atrium_scene.js"
    assert manifest["axis_conversion"] == "Y-up to Z-up"
    assert manifest["floors"] == sorted(
        manifest["floors"],
        key=lambda item: item["floor_name"],
    ), "floors 必须按 floor_name 升序排序"
    assert manifest == expected_manifest_contract()


def test_floor_obj_file_set_matches_manifest():
    expected_files = sorted(item["merged_obj_file"].split("/", 1)[1] for item in EXPECTED["floors"])
    actual_files = sorted(path.name for path in FLOOR_DIR.glob("*.obj"))
    assert actual_files == expected_files


def test_floor_obj_geometry_matches_expected_zup_export():
    for floor in EXPECTED["floors"]:
        obj_path = OUTPUT_DIR / floor["merged_obj_file"]
        actual_vertices = canonicalize_vertices(parse_obj_vertices(obj_path))
        expected_vertices = canonicalize_vertices(
            np.asarray(floor["vertices"], dtype=np.float64)
        )

        assert len(actual_vertices) > 0, f"{obj_path} 不包含任何顶点"
        assert actual_vertices.shape == expected_vertices.shape, (
            f"{floor['floor_name']} 顶点集合大小不匹配: "
            f"{actual_vertices.shape} vs {expected_vertices.shape}"
        )
        assert np.allclose(actual_vertices, expected_vertices, atol=1e-6), (
            f"{floor['floor_name']} 的 OBJ 与要求的 Z-up 导出结果不一致"
        )
