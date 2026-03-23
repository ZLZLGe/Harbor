import os

import numpy as np


OUTPUT_OBJ = "/root/output/studio_display.obj"
GROUND_TRUTH_OBJ = "/root/ground_truth/studio_display.obj"


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


def chamfer_distance(points_a, points_b):
    directed_a = max(np.min(np.linalg.norm(points_b - point, axis=1)) for point in points_a)
    directed_b = max(np.min(np.linalg.norm(points_a - point, axis=1)) for point in points_b)
    return float(directed_a + directed_b)


def test_output_exists():
    assert os.path.exists(OUTPUT_OBJ), f"missing output OBJ: {OUTPUT_OBJ}"
    assert os.path.getsize(OUTPUT_OBJ) > 0


def test_geometry_matches_ground_truth():
    output_vertices, output_faces = parse_obj(OUTPUT_OBJ)
    gt_vertices, gt_faces = parse_obj(GROUND_TRUTH_OBJ)

    assert len(output_vertices) > 0
    assert len(gt_vertices) > 0
    assert output_vertices.shape == gt_vertices.shape
    assert output_faces == gt_faces

    distance = chamfer_distance(output_vertices, gt_vertices)
    assert distance < 1e-5
