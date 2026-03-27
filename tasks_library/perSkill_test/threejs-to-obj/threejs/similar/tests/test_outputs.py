import json
import math
import os
import subprocess
import tempfile


MANIFEST_PATH = "/root/output/link_manifest.json"
LINK_DIR = "/root/output/links"


def load_expected():
    with tempfile.TemporaryDirectory(dir="/root") as temp_dir:
        ref_path = os.path.join(temp_dir, "reference_expected.mjs")
        with open("/tests/reference_expected.mjs", "r", encoding="utf-8") as src:
            with open(ref_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        output = subprocess.check_output(
            ["node", ref_path],
            text=True,
        )
        return json.loads(output)


def parse_obj_metrics(path):
    vertices = []
    face_count = 0
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line.startswith("v "):
                _, x, y, z = line.split()
                vertices.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                face_count += 1
    assert vertices, f"OBJ file has no vertices: {path}"
    xs = [value[0] for value in vertices]
    ys = [value[1] for value in vertices]
    zs = [value[2] for value in vertices]
    centroid = [
        round(sum(xs) / len(xs), 6),
        round(sum(ys) / len(ys), 6),
        round(sum(zs) / len(zs), 6),
    ]
    return {
        "vertex_count": len(vertices),
        "face_count": face_count,
        "min": [round(min(xs), 6), round(min(ys), 6), round(min(zs), 6)],
        "max": [round(max(xs), 6), round(max(ys), 6), round(max(zs), 6)],
        "centroid": centroid,
    }


def assert_close_list(actual, expected):
    assert len(actual) == len(expected)
    for actual_value, expected_value in zip(actual, expected):
        assert math.isclose(actual_value, expected_value, abs_tol=1e-5), (
            f"{actual} != {expected}"
        )


def test_manifest_exists():
    assert os.path.exists(MANIFEST_PATH), f"Missing manifest: {MANIFEST_PATH}"


def test_manifest_matches_expected_structure():
    expected = load_expected()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    assert manifest["scene_name"] == expected["scene_name"]
    assert isinstance(manifest["parts"], list)
    assert [part["name"] for part in manifest["parts"]] == [
        part["name"] for part in expected["parts"]
    ]

    for actual_part, expected_part in zip(manifest["parts"], expected["parts"]):
        assert actual_part["name"] == expected_part["name"]
        assert actual_part["parent"] == expected_part["parent"]
        assert actual_part["obj_file"] == expected_part["obj_file"]
        assert actual_part["vertex_count"] == expected_part["vertex_count"]
        assert actual_part["face_count"] == expected_part["face_count"]


def test_obj_files_exist_and_match_reference_geometry():
    expected = load_expected()
    for part in expected["parts"]:
        obj_path = os.path.join("/root/output", part["obj_file"])
        assert os.path.exists(obj_path), f"Missing OBJ file: {obj_path}"
        metrics = parse_obj_metrics(obj_path)
        assert metrics["vertex_count"] == part["vertex_count"]
        assert metrics["face_count"] == part["face_count"]
        assert_close_list(metrics["min"], part["min"])
        assert_close_list(metrics["max"], part["max"])
        assert_close_list(metrics["centroid"], part["centroid"])


def test_only_expected_obj_files_are_present():
    expected = load_expected()
    expected_names = {os.path.basename(part["obj_file"]) for part in expected["parts"]}
    actual_names = {
        name for name in os.listdir(LINK_DIR) if name.endswith(".obj")
    }
    assert actual_names == expected_names
