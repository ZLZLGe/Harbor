import json
from pathlib import Path


OUTPUT_ROOT = Path("/root/output")
GT_ROOT = Path("/root/ground_truth")
MANIFEST = Path("/root/similar_component_manifest.json")
GT_MANIFEST = GT_ROOT / "manifest.json"


def parse_obj(path: Path):
    vertices = []
    faces = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            _, x, y, z = line.split()
            vertices.append((round(float(x), 6), round(float(y), 6), round(float(z), 6)))
        elif line.startswith("f "):
            faces.append(line.strip())
    return sorted(vertices), faces


def assert_obj_equal(actual: Path, expected: Path):
    actual_vertices, actual_faces = parse_obj(actual)
    expected_vertices, expected_faces = parse_obj(expected)
    assert actual_vertices == expected_vertices, f"vertex mismatch for {actual}"
    assert len(actual_faces) == len(expected_faces), f"face count mismatch for {actual}"


def main():
    assert MANIFEST.exists(), "missing manifest output"
    assert GT_MANIFEST.exists(), "missing generated ground truth manifest"

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected_manifest = json.loads(GT_MANIFEST.read_text(encoding="utf-8"))
    assert manifest == expected_manifest, "manifest content mismatch"

    mesh_root = OUTPUT_ROOT / "component_meshes"
    gt_mesh_root = GT_ROOT / "component_meshes"
    link_root = OUTPUT_ROOT / "component_links"
    gt_link_root = GT_ROOT / "component_links"

    assert mesh_root.exists(), "missing component_meshes directory"
    assert link_root.exists(), "missing component_links directory"

    out_components = sorted(p.name for p in mesh_root.iterdir() if p.is_dir())
    gt_components = sorted(p.name for p in gt_mesh_root.iterdir() if p.is_dir())
    assert out_components == gt_components, "component directories mismatch"

    for component in gt_components:
        out_dir = mesh_root / component
        gt_dir = gt_mesh_root / component
        out_files = sorted(p.name for p in out_dir.glob("*.obj"))
        gt_files = sorted(p.name for p in gt_dir.glob("*.obj"))
        assert out_files == gt_files, f"mesh file list mismatch for {component}"
        for filename in gt_files:
            assert_obj_equal(out_dir / filename, gt_dir / filename)

        assert_obj_equal(link_root / f"{component}.obj", gt_link_root / f"{component}.obj")


if __name__ == "__main__":
    main()
