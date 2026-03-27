import json
import math
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET


URDF_PATH = "/root/output/pallet_sorter.urdf"
MESH_DIR = "/root/output/meshes"


def load_expected():
    with tempfile.TemporaryDirectory(dir="/root") as temp_dir:
        ref_path = os.path.join(temp_dir, "reference_expected.mjs")
        with open("/tests/reference_expected.mjs", "r", encoding="utf-8") as src:
            with open(ref_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        output = subprocess.check_output(["node", ref_path], text=True)
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
    return {
        "vertex_count": len(vertices),
        "face_count": face_count,
        "min": [round(min(xs), 6), round(min(ys), 6), round(min(zs), 6)],
        "max": [round(max(xs), 6), round(max(ys), 6), round(max(zs), 6)],
    }


def assert_close_list(actual, expected):
    for actual_value, expected_value in zip(actual, expected):
        assert math.isclose(actual_value, expected_value, abs_tol=1e-5), (
            f"{actual} != {expected}"
        )


def test_urdf_exists():
    assert os.path.exists(URDF_PATH), f"Missing URDF: {URDF_PATH}"


def test_urdf_matches_expected_structure():
    expected = load_expected()
    tree = ET.parse(URDF_PATH)
    robot = tree.getroot()

    assert robot.tag == "robot"
    assert robot.attrib["name"] == expected["robot_name"]

    links = []
    for link in robot.findall("link"):
        mesh = link.find("./visual/geometry/mesh")
        links.append((link.attrib["name"], mesh.attrib["filename"]))
    assert links == [(name, f"meshes/{name}.obj") for name in expected["links"]]

    joints = []
    for joint in robot.findall("joint"):
        joints.append(
            {
                "name": joint.attrib["name"],
                "type": joint.attrib["type"],
                "parent": joint.find("parent").attrib["link"],
                "child": joint.find("child").attrib["link"],
            }
        )
    assert joints == expected["joints"]


def test_mesh_files_match_reference_geometry():
    expected = load_expected()
    expected_names = {f"{entry['name']}.obj" for entry in expected["meshes"]}
    actual_names = {name for name in os.listdir(MESH_DIR) if name.endswith(".obj")}
    assert actual_names == expected_names

    for entry in expected["meshes"]:
        mesh_path = os.path.join(MESH_DIR, f"{entry['name']}.obj")
        metrics = parse_obj_metrics(mesh_path)
        assert metrics["vertex_count"] == entry["vertex_count"]
        assert metrics["face_count"] == entry["face_count"]
        assert_close_list(metrics["min"], entry["min"])
        assert_close_list(metrics["max"], entry["max"])
