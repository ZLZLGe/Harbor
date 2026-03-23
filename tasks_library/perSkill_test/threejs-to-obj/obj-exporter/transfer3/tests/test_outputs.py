import hashlib
import os

import numpy as np


OUTPUT_OBJ = "/root/output/light_canopy.obj"
GROUND_TRUTH_OBJ = "/root/ground_truth/light_canopy.obj"


def parse_obj(path):
    vertices = []
    face_count = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z = line.strip().split()
                vertices.append([float(x), float(y), float(z)])
            elif line.startswith("f "):
                face_count += 1
    return np.array(vertices, dtype=np.float64), face_count


def normalize(vertices):
    rounded = np.round(vertices, 6)
    order = np.lexsort((rounded[:, 2], rounded[:, 1], rounded[:, 0]))
    return rounded[order]


def canonical_hash(vertices):
    rows = ["{:.6f},{:.6f},{:.6f}".format(*vertex) for vertex in normalize(vertices)]
    payload = "\n".join(rows).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_output_exists():
    assert os.path.exists(OUTPUT_OBJ), f"missing output OBJ: {OUTPUT_OBJ}"


def test_geometry_signature_matches_ground_truth():
    produced, produced_faces = parse_obj(OUTPUT_OBJ)
    expected, expected_faces = parse_obj(GROUND_TRUTH_OBJ)
    assert produced.shape == expected.shape
    assert produced_faces == expected_faces
    assert canonical_hash(produced) == canonical_hash(expected)


def test_centroid_matches_ground_truth():
    produced, _ = parse_obj(OUTPUT_OBJ)
    expected, _ = parse_obj(GROUND_TRUTH_OBJ)
    assert np.allclose(produced.mean(axis=0), expected.mean(axis=0), atol=1e-6)
