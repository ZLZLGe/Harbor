import json
from pathlib import Path


OUTPUT_MANIFEST = Path("/root/output/wind_turbine_manifest.json")
EXPECTED_MANIFEST = Path("/root/expected_manifest.json")
EPS = 1e-5


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_obj_vertices(path):
    vertices = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith("v "):
                continue
            _, x, y, z = line.strip().split()
            vertices.append([float(x), float(y), float(z)])
    return vertices


def compute_bbox(vertices):
    mins = [min(values) for values in zip(*vertices)]
    maxs = [max(values) for values in zip(*vertices)]
    return {
        "min": mins,
        "max": maxs,
    }


def assert_bbox_close(actual, expected):
    for key in ("min", "max"):
        for actual_value, expected_value in zip(actual[key], expected[key]):
            assert abs(actual_value - expected_value) <= EPS, (
                f"bbox mismatch for {key}: actual={actual}, expected={expected}"
            )


class TestWindTurbineExport:
    def test_manifest_exists(self):
        assert OUTPUT_MANIFEST.exists(), f"Missing manifest: {OUTPUT_MANIFEST}"

    def test_manifest_matches_expected_parts(self):
        actual = load_json(OUTPUT_MANIFEST)
        expected = load_json(EXPECTED_MANIFEST)

        assert actual["scene_file"] == "/root/data/wind_turbine.js"
        assert actual["part_count"] == expected["part_count"]
        assert len(actual["parts"]) == expected["part_count"]

        actual_names = [part["part_name"] for part in actual["parts"]]
        expected_names = [part["part_name"] for part in expected["parts"]]
        assert actual_names == expected_names
        assert actual_names == sorted(actual_names)

        for actual_part, expected_part in zip(actual["parts"], expected["parts"]):
            assert actual_part["mesh_count"] == expected_part["mesh_count"]
            assert actual_part["mesh_names"] == expected_part["mesh_names"]
            assert actual_part["mesh_names"] == sorted(actual_part["mesh_names"])
            assert actual_part["mesh_obj_paths"] == expected_part["mesh_obj_paths"]
            assert actual_part["mesh_obj_paths"] == sorted(actual_part["mesh_obj_paths"])
            assert actual_part["merged_obj_path"] == expected_part["merged_obj_path"]
            assert actual_part["vertex_count"] == expected_part["vertex_count"]
            assert_bbox_close(actual_part["bbox"], expected_part["bbox"])

    def test_each_individual_obj_matches_mesh_stats(self):
        expected = load_json(EXPECTED_MANIFEST)

        for part in expected["parts"]:
            for mesh in part["meshes"]:
                obj_path = Path(mesh["obj_path"])
                assert obj_path.exists(), f"Missing mesh OBJ: {obj_path}"
                vertices = parse_obj_vertices(obj_path)
                assert vertices, f"Mesh OBJ has no vertices: {obj_path}"
                assert len(vertices) == mesh["vertex_count"]
                assert_bbox_close(compute_bbox(vertices), mesh["bbox"])

    def test_each_merged_obj_matches_manifest_stats(self):
        actual = load_json(OUTPUT_MANIFEST)

        for part in actual["parts"]:
            obj_path = Path(part["merged_obj_path"])
            assert obj_path.exists(), f"Missing merged OBJ: {obj_path}"
            vertices = parse_obj_vertices(obj_path)
            assert vertices, f"Merged OBJ has no vertices: {obj_path}"
            assert len(vertices) == part["vertex_count"]
            assert_bbox_close(compute_bbox(vertices), part["bbox"])
