import json
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


def assert_tree_matches(relative_root: str):
    out_root = OUTPUT_DIR / relative_root
    gt_root = GROUND_TRUTH_DIR / relative_root
    assert gt_root.exists(), f"missing ground truth directory: {gt_root}"
    assert out_root.exists(), f"missing output directory: {out_root}"

    gt_files = sorted(path.relative_to(gt_root) for path in gt_root.rglob("*.obj"))
    out_files = sorted(path.relative_to(out_root) for path in out_root.rglob("*.obj"))
    assert out_files == gt_files, f"OBJ tree mismatch for {relative_root}"

    for rel_path in gt_files:
        out_file = out_root / rel_path
        gt_file = gt_root / rel_path
        assert parse_vertices(out_file) == parse_vertices(gt_file), (
            f"vertex mismatch for {rel_path}"
        )


def main():
    inventory_path = OUTPUT_DIR / "part_inventory.json"
    gt_inventory_path = GROUND_TRUTH_DIR / "part_inventory.json"

    assert inventory_path.exists(), "missing /root/output/part_inventory.json"
    assert json.loads(inventory_path.read_text()) == json.loads(gt_inventory_path.read_text()), (
        "part_inventory.json does not match ground truth"
    )

    assert_tree_matches("part_meshes")
    assert_tree_matches("links")


if __name__ == "__main__":
    main()
