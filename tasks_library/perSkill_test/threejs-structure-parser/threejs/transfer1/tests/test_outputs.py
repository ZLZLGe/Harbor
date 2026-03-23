import xml.etree.ElementTree as ET
from pathlib import Path


OUTPUT_DIR = Path("/root/output")
GROUND_TRUTH_DIR = Path("/root/ground_truth")


def parse_vertices(path: Path):
    vertices = []
    for line in path.read_text().splitlines():
        if not line.startswith("v "):
            continue
        _, x, y, z, *_ = line.split()
        vertices.append(tuple(round(float(value), 6) for value in (x, y, z)))
    return sorted(vertices)


def normalize_urdf(path: Path):
    root = ET.fromstring(path.read_text())
    assert root.tag == "robot", "root element must be <robot>"
    links = []
    joints = []

    for link in root.findall("link"):
      mesh = link.find("./visual/geometry/mesh")
      links.append(
          {
              "name": link.attrib["name"],
              "mesh": mesh.attrib["filename"] if mesh is not None else None,
          }
      )

    for joint in root.findall("joint"):
      joints.append(
          {
              "name": joint.attrib["name"],
              "type": joint.attrib["type"],
              "parent": joint.find("parent").attrib["link"],
              "child": joint.find("child").attrib["link"],
          }
      )

    return {
        "robot_name": root.attrib.get("name"),
        "links": sorted(links, key=lambda item: item["name"]),
        "joints": sorted(joints, key=lambda item: item["name"]),
    }


def main():
    output_urdf = OUTPUT_DIR / "robot_arm.urdf"
    ground_truth_urdf = GROUND_TRUTH_DIR / "robot_arm.urdf"
    assert output_urdf.exists(), "missing /root/output/robot_arm.urdf"
    assert normalize_urdf(output_urdf) == normalize_urdf(ground_truth_urdf), (
        "URDF content does not match ground truth"
    )

    output_meshes = OUTPUT_DIR / "meshes"
    ground_truth_meshes = GROUND_TRUTH_DIR / "meshes"
    assert output_meshes.exists(), "missing /root/output/meshes"

    expected = sorted(path.name for path in ground_truth_meshes.glob("*.obj"))
    actual = sorted(path.name for path in output_meshes.glob("*.obj"))
    assert actual == expected, "mesh file list does not match ground truth"

    for name in expected:
        assert parse_vertices(output_meshes / name) == parse_vertices(ground_truth_meshes / name), (
            f"vertex mismatch for {name}"
        )


if __name__ == "__main__":
    main()
