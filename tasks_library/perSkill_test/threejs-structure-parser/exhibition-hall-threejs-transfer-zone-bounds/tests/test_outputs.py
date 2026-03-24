import json
from pathlib import Path


OUTPUT_JSON = Path("/root/output/zone_bounds_report.json")
EXPECTED_JSON = Path("/root/expected_zone_report.json")
EPS = 1e-5


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def assert_vector_close(actual, expected):
    assert len(actual) == len(expected)
    for actual_value, expected_value in zip(actual, expected):
        assert abs(actual_value - expected_value) <= EPS, (
            f"vector mismatch: actual={actual}, expected={expected}"
        )


def assert_bbox_close(actual, expected):
    assert_vector_close(actual["min"], expected["min"])
    assert_vector_close(actual["max"], expected["max"])


class TestZoneBoundsReport:
    def test_primary_output_exists(self):
        assert OUTPUT_JSON.exists(), f"Missing report: {OUTPUT_JSON}"

    def test_report_matches_expected(self):
        actual = load_json(OUTPUT_JSON)
        expected = load_json(EXPECTED_JSON)

        assert actual["scene_file"] == "/root/data/exhibition_hall.js"
        assert actual["scene_file"] == expected["scene_file"]
        assert actual["zone_count"] == expected["zone_count"]
        assert len(actual["zones"]) == expected["zone_count"]

        actual_zone_names = [zone["zone_name"] for zone in actual["zones"]]
        expected_zone_names = [zone["zone_name"] for zone in expected["zones"]]
        assert actual_zone_names == expected_zone_names
        assert actual_zone_names == sorted(actual_zone_names)

        for actual_zone, expected_zone in zip(actual["zones"], expected["zones"]):
            assert actual_zone["parent_zone"] == expected_zone["parent_zone"]
            assert actual_zone["child_zones"] == expected_zone["child_zones"]
            assert actual_zone["child_zones"] == sorted(actual_zone["child_zones"])
            assert actual_zone["mesh_count"] == expected_zone["mesh_count"]
            assert actual_zone["direct_mesh_names"] == expected_zone["direct_mesh_names"]
            assert actual_zone["direct_mesh_names"] == sorted(actual_zone["direct_mesh_names"])
            assert_bbox_close(actual_zone["world_bbox"], expected_zone["world_bbox"])

    def test_mesh_count_matches_mesh_name_list(self):
        actual = load_json(OUTPUT_JSON)

        for zone in actual["zones"]:
            assert zone["mesh_count"] == len(zone["direct_mesh_names"])
            assert zone["mesh_count"] > 0

    def test_parent_child_links_are_consistent(self):
        actual = load_json(OUTPUT_JSON)
        zones_by_name = {zone["zone_name"]: zone for zone in actual["zones"]}

        for zone in actual["zones"]:
            for child_name in zone["child_zones"]:
                assert child_name in zones_by_name, f"Unknown child zone {child_name}"
                assert zones_by_name[child_name]["parent_zone"] == zone["zone_name"]
