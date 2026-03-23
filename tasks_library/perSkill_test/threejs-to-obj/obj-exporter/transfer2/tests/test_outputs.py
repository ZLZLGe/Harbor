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


def bounding_box(vertices):
    return vertices.min(axis=0), vertices.max(axis=0)


def hausdorff_distance(points_a, points_b):
    directed_a = max(np.min(np.linalg.norm(points_b - point, axis=1)) for point in points_a)
    directed_b = max(np.min(np.linalg.norm(points_a - point, axis=1)) for point in points_b)
    return float(max(directed_a, directed_b))


OUTPUT_OBJ = "/root/output/safety_barrier.obj"
GROUND_TRUTH_OBJ = "/root/ground_truth/safety_barrier.obj"


def test_output_exists():
    assert os.path.exists(OUTPUT_OBJ), f"missing output OBJ: {OUTPUT_OBJ}"


def test_geometry_matches_ground_truth_shape():
    produced = parse_obj_vertices(OUTPUT_OBJ)
    expected = parse_obj_vertices(GROUND_TRUTH_OBJ)
    assert produced.shape == expected.shape, "vertex array shape mismatch"
    assert hausdorff_distance(produced, expected) < 1e-5


def test_bounding_box_matches_ground_truth():
    produced = parse_obj_vertices(OUTPUT_OBJ)
    expected = parse_obj_vertices(GROUND_TRUTH_OBJ)
    produced_min, produced_max = bounding_box(produced)
    expected_min, expected_max = bounding_box(expected)
    assert np.allclose(produced_min, expected_min, atol=1e-6)
    assert np.allclose(produced_max, expected_max, atol=1e-6)
