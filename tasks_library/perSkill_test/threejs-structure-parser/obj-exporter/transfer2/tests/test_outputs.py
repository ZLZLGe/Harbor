from pathlib import Path


LEDGER = Path("/root/transfer2_mesh_metrics.csv")
GT_LEDGER = Path("/root/ground_truth/ledger.csv")
OUTPUT_DIR = Path("/root/output/audit_meshes")
GT_DIR = Path("/root/ground_truth/audit_meshes")


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
    assert LEDGER.exists(), "missing transfer2 ledger"
    assert GT_LEDGER.exists(), "missing generated transfer2 ledger"
    assert LEDGER.read_text(encoding="utf-8") == GT_LEDGER.read_text(encoding="utf-8"), "ledger mismatch"

    actual_components = sorted(p.name for p in OUTPUT_DIR.iterdir() if p.is_dir())
    expected_components = sorted(p.name for p in GT_DIR.iterdir() if p.is_dir())
    assert actual_components == expected_components, "component directory mismatch"

    for component in expected_components:
        actual_files = sorted(p.name for p in (OUTPUT_DIR / component).glob("*.obj"))
        expected_files = sorted(p.name for p in (GT_DIR / component).glob("*.obj"))
        assert actual_files == expected_files, f"mesh list mismatch for {component}"
        for filename in expected_files:
            assert_obj_equal(OUTPUT_DIR / component / filename, GT_DIR / component / filename)


if __name__ == "__main__":
    main()
