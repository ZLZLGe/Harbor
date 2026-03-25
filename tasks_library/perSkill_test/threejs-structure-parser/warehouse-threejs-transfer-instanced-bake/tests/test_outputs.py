import json
import subprocess
from pathlib import Path

import numpy as np


OUTPUT_DIR = Path("/root/output")
OBJ_PATH = OUTPUT_DIR / "baked_scene.obj"
REPORT_PATH = OUTPUT_DIR / "instance_report.json"


def parse_obj_vertices(file_path: Path) -> np.ndarray:
    vertices = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z, *_ = line.strip().split()
                vertices.append([float(x), float(y), float(z)])
    return np.asarray(vertices, dtype=np.float64)


def canonical_unique(points: np.ndarray) -> np.ndarray:
    if len(points) == 0:
        return points.reshape(0, 3)
    rounded = np.round(points, decimals=6)
    unique = np.unique(rounded, axis=0)
    order = np.lexsort((unique[:, 2], unique[:, 1], unique[:, 0]))
    return unique[order]


def load_expected() -> dict:
    script = r"""
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { pathToFileURL } from 'url';

const sceneModule = await import(pathToFileURL('/root/data/warehouse_scene.js').href);
const root = sceneModule.createScene();
root.updateMatrixWorld(true);

function bakeGeometry(geometry, matrix) {
  let baked = geometry.clone();
  baked.applyMatrix4(matrix);
  if (baked.index) baked = baked.toNonIndexed();
  if (!baked.attributes.normal) baked.computeVertexNormals();
  return baked;
}

const geometries = [];
const instancedNodes = [];
let regularMeshCount = 0;
const instanceMatrix = new THREE.Matrix4();
const worldMatrix = new THREE.Matrix4();

root.traverse((object) => {
  if (object.isInstancedMesh) {
    instancedNodes.push({
      node_name: object.name,
      instance_count: object.count,
    });
    for (let i = 0; i < object.count; i += 1) {
      object.getMatrixAt(i, instanceMatrix);
      worldMatrix.copy(object.matrixWorld).multiply(instanceMatrix);
      geometries.push(bakeGeometry(object.geometry, worldMatrix));
    }
    return;
  }

  if (object.isMesh) {
    regularMeshCount += 1;
    geometries.push(bakeGeometry(object.geometry, object.matrixWorld));
  }
});

const merged = mergeGeometries(geometries, false);
const positions = Array.from(merged.attributes.position.array);
const vertices = [];
for (let i = 0; i < positions.length; i += 3) {
  vertices.push([positions[i], positions[i + 1], positions[i + 2]]);
}

instancedNodes.sort((a, b) => a.node_name.localeCompare(b.node_name));
const totalInstances = instancedNodes.reduce((sum, item) => sum + item.instance_count, 0);

console.log(JSON.stringify({
  scene_file: 'warehouse_scene.js',
  merged_obj: 'baked_scene.obj',
  instanced_nodes: instancedNodes,
  total_instances: totalInstances,
  total_baked_primitives: regularMeshCount + totalInstances,
  vertices,
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


def test_required_outputs_exist():
    assert OBJ_PATH.exists(), "缺少 /root/output/baked_scene.obj"
    assert REPORT_PATH.exists(), "缺少 /root/output/instance_report.json"


def test_instance_report_matches_contract():
    with REPORT_PATH.open("r", encoding="utf-8") as handle:
        report = json.load(handle)

    assert report["scene_file"] == "warehouse_scene.js"
    assert report["merged_obj"] == "baked_scene.obj"
    assert isinstance(report["instanced_nodes"], list)
    assert report["instanced_nodes"] == sorted(
        report["instanced_nodes"],
        key=lambda item: item["node_name"],
    ), "instanced_nodes 必须按 node_name 升序排序"

    assert report["instanced_nodes"] == EXPECTED["instanced_nodes"]
    assert report["total_instances"] == EXPECTED["total_instances"]
    assert report["total_baked_primitives"] == EXPECTED["total_baked_primitives"]


def test_instance_report_only_lists_instanced_nodes():
    with REPORT_PATH.open("r", encoding="utf-8") as handle:
        report = json.load(handle)

    node_names = {item["node_name"] for item in report["instanced_nodes"]}
    assert "floor_plate" not in node_names
    assert "rear_wall" not in node_names
    assert "pallet_base" not in node_names


def test_baked_obj_contains_expected_geometry():
    actual_vertices = canonical_unique(parse_obj_vertices(OBJ_PATH))
    expected_vertices = canonical_unique(
        np.asarray(EXPECTED["vertices"], dtype=np.float64)
    )

    assert len(actual_vertices) > 0, "OBJ 不包含任何顶点"
    assert actual_vertices.shape == expected_vertices.shape, (
        f"顶点集合大小不匹配: {actual_vertices.shape} vs {expected_vertices.shape}"
    )
    assert np.allclose(actual_vertices, expected_vertices, atol=1e-6), (
        "baked_scene.obj 的世界坐标几何与场景展开结果不一致"
    )
