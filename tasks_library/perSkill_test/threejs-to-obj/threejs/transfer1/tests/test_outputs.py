import json
import os
import subprocess
import tempfile


REPORT_PATH = "/root/output/ownership_report.json"


def load_expected():
    with tempfile.TemporaryDirectory(dir="/root") as temp_dir:
        ref_path = os.path.join(temp_dir, "reference_expected.mjs")
        with open("/tests/reference_expected.mjs", "r", encoding="utf-8") as src:
            with open(ref_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        output = subprocess.check_output(["node", ref_path], text=True)
        return json.loads(output)


def test_report_exists():
    assert os.path.exists(REPORT_PATH), f"Missing report: {REPORT_PATH}"


def test_report_matches_reference():
    expected = load_expected()
    with open(REPORT_PATH, "r", encoding="utf-8") as handle:
      actual = json.load(handle)

    assert actual == expected


def test_report_is_sorted_and_complete():
    with open(REPORT_PATH, "r", encoding="utf-8") as handle:
        actual = json.load(handle)

    names = [part["name"] for part in actual["parts"]]
    assert names == sorted(names)
    for part in actual["parts"]:
        assert sorted(part["child_parts"]) == part["child_parts"]
        assert isinstance(part["mesh_count"], int)
        assert isinstance(part["instanced_instance_count"], int)
        assert isinstance(part["owned_triangle_count"], int)
        assert part["mesh_count"] > 0 or part["instanced_instance_count"] > 0
