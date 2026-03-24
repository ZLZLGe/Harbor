import json
from pathlib import Path


OUTPUT_JSON = Path("/root/output/lighting_inventory.json")
EXPECTED_JSON = Path("/root/expected_inventory.json")
RIG_MESH_DIR = Path("/root/output/rig_meshes")
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
    return {"min": mins, "max": maxs}


def assert_vector_close(actual, expected):
    assert len(actual) == len(expected)
    for actual_value, expected_value in zip(actual, expected):
        assert abs(actual_value - expected_value) <= EPS, (
            f"vector mismatch: actual={actual}, expected={expected}"
        )


def assert_bbox_close(actual, expected):
    assert_vector_close(actual["min"], expected["min"])
    assert_vector_close(actual["max"], expected["max"])


class TestLightingInventory:
    def test_primary_output_exists(self):
        assert OUTPUT_JSON.exists(), f"Missing inventory file: {OUTPUT_JSON}"

    def test_inventory_matches_expected(self):
        actual = load_json(OUTPUT_JSON)
        expected = load_json(EXPECTED_JSON)

        assert actual["scene_file"] == "/root/data/stadium_lighting.js"
        assert actual["rig_count"] == expected["rig_count"]
        assert actual["total_fixture_count"] == expected["total_fixture_count"]
        assert len(actual["rigs"]) == expected["rig_count"]

        actual_rig_names = [rig["rig_name"] for rig in actual["rigs"]]
        expected_rig_names = [rig["rig_name"] for rig in expected["rigs"]]
        assert actual_rig_names == expected_rig_names
        assert actual_rig_names == sorted(actual_rig_names)

        for actual_rig, expected_rig in zip(actual["rigs"], expected["rigs"]):
            assert actual_rig["fixture_count"] == expected_rig["fixture_count"]
            assert actual_rig["merged_obj_path"] == expected_rig["merged_obj_path"]
            assert actual_rig["fixture_types"] == expected_rig["fixture_types"]
            assert actual_rig["fixture_types"] == sorted(
                actual_rig["fixture_types"], key=lambda item: item["type_name"]
            )
            assert_bbox_close(actual_rig["bbox"], expected_rig["bbox"])

            actual_fixtures = actual_rig["fixtures"]
            expected_fixtures = expected_rig["fixtures"]
            assert len(actual_fixtures) == len(expected_fixtures)

            actual_fixture_names = [fixture["fixture_name"] for fixture in actual_fixtures]
            expected_fixture_names = [fixture["fixture_name"] for fixture in expected_fixtures]
            assert actual_fixture_names == expected_fixture_names
            assert actual_fixture_names == sorted(actual_fixture_names)

            for actual_fixture, expected_fixture in zip(actual_fixtures, expected_fixtures):
                assert actual_fixture["source_type"] == expected_fixture["source_type"]
                assert_vector_close(actual_fixture["center"], expected_fixture["center"])
                assert_bbox_close(actual_fixture["bbox"], expected_fixture["bbox"])

    def test_rig_meshes_exist_and_match_bbox(self):
        expected = load_json(EXPECTED_JSON)

        assert RIG_MESH_DIR.exists(), f"Missing rig mesh directory: {RIG_MESH_DIR}"
        actual_files = sorted(path.name for path in RIG_MESH_DIR.glob("*.obj"))
        expected_files = [f"{rig['rig_name']}.obj" for rig in expected["rigs"]]
        assert actual_files == expected_files

        for rig in expected["rigs"]:
            obj_path = Path(rig["merged_obj_path"])
            assert obj_path.exists(), f"Missing rig OBJ: {obj_path}"
            vertices = parse_obj_vertices(obj_path)
            assert vertices, f"Rig OBJ has no vertices: {obj_path}"
            assert_bbox_close(compute_bbox(vertices), rig["bbox"])
