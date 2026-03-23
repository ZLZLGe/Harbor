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
    output_manifest = OUTPUT_DIR / "fabrication_manifest.json"
    ground_truth_manifest = GROUND_TRUTH_DIR / "fabrication_manifest.json"
    assert output_manifest.exists(), "missing /root/output/fabrication_manifest.json"
    assert json.loads(output_manifest.read_text()) == json.loads(ground_truth_manifest.read_text()), (
        "fabrication manifest does not match ground truth"
    )

    output_links = OUTPUT_DIR / "fabrication_links"
    ground_truth_links = GROUND_TRUTH_DIR / "fabrication_links"
    assert output_links.exists(), "missing /root/output/fabrication_links"

    expected = sorted(path.name for path in ground_truth_links.glob("*.obj"))
    actual = sorted(path.name for path in output_links.glob("*.obj"))
    assert actual == expected, "fabrication OBJ file list does not match ground truth"

    for name in expected:
        assert parse_vertices(output_links / name) == parse_vertices(ground_truth_links / name), (
            f"vertex mismatch for {name}"
        )


if __name__ == "__main__":
    main()
