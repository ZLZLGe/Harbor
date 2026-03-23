import json
from pathlib import Path


REPORT = Path("/root/transfer3_bundle_report.json")
GT_REPORT = Path("/root/ground_truth/report.json")
OUTPUT_DIR = Path("/root/output/bundles")
GT_DIR = Path("/root/ground_truth/bundles")


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
    assert REPORT.exists(), "missing transfer3 report"
    assert GT_REPORT.exists(), "missing generated transfer3 report"
    assert json.loads(REPORT.read_text(encoding="utf-8")) == json.loads(GT_REPORT.read_text(encoding="utf-8")), "report mismatch"

    expected_files = sorted(p.name for p in GT_DIR.glob("*.obj"))
    actual_files = sorted(p.name for p in OUTPUT_DIR.glob("*.obj"))
    assert actual_files == expected_files, "bundle obj list mismatch"

    for filename in expected_files:
        assert_obj_equal(OUTPUT_DIR / filename, GT_DIR / filename)


if __name__ == "__main__":
    main()
