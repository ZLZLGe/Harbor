import os

import numpy as np


def parse_obj_vertices(path):
    vertices = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z = line.strip().split()
                vertices.append([float(x), float(y), float(z)])
    return np.array(vertices, dtype=np.float64)


def face_count(path):
    with open(path, "r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.startswith("f "))


def canonical_vertices(vertices):
    rounded = np.round(vertices, 6)
    order = np.lexsort((rounded[:, 2], rounded[:, 1], rounded[:, 0]))
    return rounded[order]


OUTPUT_OBJ = "/root/output/info_kiosk.obj"
GROUND_TRUTH_OBJ = "/root/ground_truth/info_kiosk.obj"


def test_output_exists():
    assert os.path.exists(OUTPUT_OBJ), f"missing output OBJ: {OUTPUT_OBJ}"


def test_vertex_set_matches_ground_truth():
    produced = parse_obj_vertices(OUTPUT_OBJ)
    expected = parse_obj_vertices(GROUND_TRUTH_OBJ)
    assert produced.shape == expected.shape, "vertex array shape mismatch"
    assert np.array_equal(canonical_vertices(produced), canonical_vertices(expected))


def test_face_count_matches_ground_truth():
    assert face_count(OUTPUT_OBJ) == face_count(GROUND_TRUTH_OBJ)
