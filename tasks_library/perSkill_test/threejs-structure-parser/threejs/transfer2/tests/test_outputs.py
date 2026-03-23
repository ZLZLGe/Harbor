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


def main():
    output_report = OUTPUT_DIR / "instance_report.json"
    ground_truth_report = GROUND_TRUTH_DIR / "instance_report.json"
    assert output_report.exists(), "missing /root/output/instance_report.json"
    assert json.loads(output_report.read_text()) == json.loads(ground_truth_report.read_text()), (
        "instance report does not match ground truth"
    )

    expected_files = sorted(
        path.relative_to(GROUND_TRUTH_DIR / "instances")
        for path in (GROUND_TRUTH_DIR / "instances").rglob("*.obj")
    )
    actual_files = sorted(
        path.relative_to(OUTPUT_DIR / "instances")
        for path in (OUTPUT_DIR / "instances").rglob("*.obj")
    )
    assert actual_files == expected_files, "instance OBJ tree does not match ground truth"

    for rel_path in expected_files:
        assert parse_vertices(OUTPUT_DIR / "instances" / rel_path) == parse_vertices(
            GROUND_TRUTH_DIR / "instances" / rel_path
        ), f"vertex mismatch for {rel_path}"


if __name__ == "__main__":
    main()
