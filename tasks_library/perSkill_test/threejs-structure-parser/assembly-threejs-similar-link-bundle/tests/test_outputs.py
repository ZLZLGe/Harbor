import json
import subprocess
from pathlib import Path

import numpy as np


OUTPUT_DIR = Path("/root/output")
INDEX_PATH = OUTPUT_DIR / "link_index.json"


def parse_obj_vertices(file_path: Path) -> np.ndarray:
    vertices = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z, *_ = line.strip().split()
                vertices.append([float(x), float(y), float(z)])
    return np.asarray(vertices, dtype=np.float64)


def canonicalize(points: np.ndarray) -> np.ndarray:
    if len(points) == 0:
        return points
    order = np.lexsort((points[:, 2], points[:, 1], points[:, 0]))
    return points[order]


def chamfer_distance(points_a: np.ndarray, points_b: np.ndarray) -> float:
    if len(points_a) == 0 or len(points_b) == 0:
        return float("inf")
    a = canonicalize(points_a)
    b = canonicalize(points_b)
    deltas = a[:, None, :] - b[None, :, :]
    distances = np.linalg.norm(deltas, axis=2)
    return float(distances.min(axis=1).mean() + distances.min(axis=0).mean())


def load_expected_structure():
    script = r"""
import * as THREE from 'three';
import { pathToFileURL } from 'url';

const inputPath = '/root/data/assembly_scene.js';
const sceneModule = await import(pathToFileURL(inputPath).href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

function serializeGeometry(geometry) {
  let baked = geometry;
  if (baked.index) baked = baked.toNonIndexed();
  const positions = Array.from(baked.attributes.position.array);
  const vertices = [];
  for (let i = 0; i < positions.length; i += 3) {
    vertices.push([positions[i], positions[i + 1], positions[i + 2]]);
  }
  return vertices;
}

function bakeGeometry(mesh) {
  let geometry = mesh.geometry.clone();
  geometry.applyMatrix4(mesh.matrixWorld);
  if (!geometry.attributes.normal) geometry.computeVertexNormals();
  return geometry;
}

const partMap = new Map();
root.traverse((object) => {
  if (object.isGroup && object.name) {
    partMap.set(object.name, { group: object, parent_part: null, meshes: [] });
  }
});

for (const part of partMap.values()) {
  let parent = part.group.parent;
  while (parent) {
    if (parent.isGroup && parent.name) {
      part.parent_part = parent.name;
      break;
    }
    parent = parent.parent;
  }
}

root.traverse((object) => {
  if (!object.isMesh) return;
  let parent = object.parent;
  while (parent) {
    if (parent.isGroup && parent.name) {
      partMap.get(parent.name).meshes.push(object);
      break;
    }
    parent = parent.parent;
  }
});

const parts = Array.from(partMap.entries())
  .filter(([, part]) => part.meshes.length > 0)
  .sort((a, b) => a[0].localeCompare(b[0]))
  .map(([partName, part]) => {
    const meshRecords = part.meshes
      .map((mesh) => {
        const geometry = bakeGeometry(mesh);
        return {
          mesh_name: mesh.name,
          vertices: serializeGeometry(geometry),
        };
      })
      .sort((a, b) => a.mesh_name.localeCompare(b.mesh_name));

    return {
      part_name: partName,
      parent_part: part.parent_part,
      mesh_names: meshRecords.map((record) => record.mesh_name),
      mesh_count: meshRecords.length,
      mesh_vertices: Object.fromEntries(
        meshRecords.map((record) => [record.mesh_name, record.vertices]),
      ),
      merged_vertices: meshRecords.flatMap((record) => record.vertices),
    };
  });

console.log(JSON.stringify({ scene_file: 'assembly_scene.js', parts }));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


EXPECTED = load_expected_structure()


def test_required_outputs_exist():
    assert INDEX_PATH.exists(), "缺少 /root/output/link_index.json"
    assert (OUTPUT_DIR / "part_meshes").is_dir(), "缺少 /root/output/part_meshes"
    assert (OUTPUT_DIR / "links").is_dir(), "缺少 /root/output/links"


def test_index_matches_contract():
    with INDEX_PATH.open("r", encoding="utf-8") as handle:
        actual = json.load(handle)

    assert actual["scene_file"] == "assembly_scene.js"
    assert isinstance(actual["parts"], list)

    actual_part_names = [part["part_name"] for part in actual["parts"]]
    expected_part_names = [part["part_name"] for part in EXPECTED["parts"]]
    assert actual_part_names == sorted(actual_part_names), "parts 必须按 part_name 升序排序"
    assert actual_part_names == expected_part_names

    for actual_part, expected_part in zip(actual["parts"], EXPECTED["parts"], strict=True):
        assert actual_part["part_name"] == expected_part["part_name"]
        assert actual_part["parent_part"] == expected_part["parent_part"]
        assert actual_part["mesh_count"] == expected_part["mesh_count"]
        assert actual_part["mesh_names"] == expected_part["mesh_names"]
        assert actual_part["mesh_obj_files"] == [
            f"part_meshes/{expected_part['part_name']}/{mesh_name}.obj"
            for mesh_name in expected_part["mesh_names"]
        ]
        assert actual_part["merged_obj_file"] == f"links/{expected_part['part_name']}.obj"


def test_output_file_layout_matches_index():
    with INDEX_PATH.open("r", encoding="utf-8") as handle:
        index_data = json.load(handle)

    expected_parts = [part["part_name"] for part in EXPECTED["parts"]]
    actual_part_dirs = sorted(
        path.name for path in (OUTPUT_DIR / "part_meshes").iterdir() if path.is_dir()
    )
    actual_link_files = sorted(
        path.name for path in (OUTPUT_DIR / "links").glob("*.obj")
    )

    assert actual_part_dirs == expected_parts
    assert actual_link_files == [f"{part_name}.obj" for part_name in expected_parts]

    for part in index_data["parts"]:
        merged_path = OUTPUT_DIR / part["merged_obj_file"]
        assert merged_path.exists(), f"缺少部件合并 OBJ: {merged_path}"
        assert part["mesh_count"] == len(part["mesh_obj_files"]) == len(part["mesh_names"])

        actual_mesh_files = sorted(
            path.name
            for path in (OUTPUT_DIR / "part_meshes" / part["part_name"]).glob("*.obj")
        )
        assert actual_mesh_files == [f"{mesh_name}.obj" for mesh_name in part["mesh_names"]]

        for relative_path, mesh_name in zip(part["mesh_obj_files"], part["mesh_names"], strict=True):
            mesh_path = OUTPUT_DIR / relative_path
            assert mesh_path.exists(), f"缺少单件 OBJ: {mesh_path}"
            assert mesh_path.stem == mesh_name


def test_mesh_geometry_matches_scene():
    threshold = 1e-5

    for part in EXPECTED["parts"]:
        for mesh_name, expected_vertices in part["mesh_vertices"].items():
            output_path = OUTPUT_DIR / "part_meshes" / part["part_name"] / f"{mesh_name}.obj"
            output_vertices = parse_obj_vertices(output_path)
            expected_array = np.asarray(expected_vertices, dtype=np.float64)

            assert len(output_vertices) > 0
            assert len(expected_array) > 0
            distance = chamfer_distance(output_vertices, expected_array)
            assert distance <= threshold, (
                f"{part['part_name']}/{mesh_name}.obj 几何不匹配，Chamfer={distance}"
            )


def test_merged_geometry_matches_scene():
    threshold = 1e-5

    for part in EXPECTED["parts"]:
        output_path = OUTPUT_DIR / "links" / f"{part['part_name']}.obj"
        output_vertices = parse_obj_vertices(output_path)
        expected_array = np.asarray(part["merged_vertices"], dtype=np.float64)

        assert len(output_vertices) > 0
        assert len(expected_array) > 0
        distance = chamfer_distance(output_vertices, expected_array)
        assert distance <= threshold, (
            f"{part['part_name']}.obj 几何不匹配，Chamfer={distance}"
        )
