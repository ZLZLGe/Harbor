import os

import numpy as np


OUTPUT_PATH = "/root/output/lamp.obj"
GROUND_TRUTH_PATH = "/root/ground_truth/lamp.obj"
CHAMFER_THRESHOLD = 1e-5


def parse_obj(filepath):
    vertices = []
    faces = []

    with open(filepath, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z = line.strip().split()[:4]
                vertices.append([float(x), float(y), float(z)])
            elif line.startswith("f "):
                faces.append(line.strip())

    return np.asarray(vertices, dtype=float), faces


def chamfer_distance(points_a, points_b):
    distances_a = []
    for point in points_a:
        distances = np.linalg.norm(points_b - point, axis=1)
        distances_a.append(np.min(distances))

    distances_b = []
    for point in points_b:
        distances = np.linalg.norm(points_a - point, axis=1)
        distances_b.append(np.min(distances))

    return float(np.mean(distances_a) + np.mean(distances_b))


def bbox_extents(points):
    minimum = points.min(axis=0)
    maximum = points.max(axis=0)
    return minimum, maximum, maximum - minimum


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), f"missing output: {OUTPUT_PATH}"
    assert os.path.getsize(OUTPUT_PATH) > 0, "output OBJ is empty"


def test_obj_has_vertices_and_faces():
    vertices, faces = parse_obj(OUTPUT_PATH)
    assert len(vertices) > 1000, "expected a non-trivial OBJ export"
    assert len(faces) > 1000, "expected triangle faces in the OBJ export"


def test_bbox_reflects_blender_z_up_rotation():
    vertices, _ = parse_obj(OUTPUT_PATH)
    _, _, extents = bbox_extents(vertices)
    assert extents[2] > extents[1] * 1.5, (
        "the exported lamp should be taller on the Z axis after the required X rotation"
    )


def test_geometry_matches_ground_truth():
    assert os.path.exists(GROUND_TRUTH_PATH), f"missing ground truth: {GROUND_TRUTH_PATH}"

    output_vertices, output_faces = parse_obj(OUTPUT_PATH)
    gt_vertices, gt_faces = parse_obj(GROUND_TRUTH_PATH)

    assert len(output_vertices) > 0
    assert len(gt_vertices) > 0

    cd = chamfer_distance(output_vertices, gt_vertices)
    assert cd < CHAMFER_THRESHOLD, f"Chamfer distance too large: {cd}"

    out_min, out_max, _ = bbox_extents(output_vertices)
    gt_min, gt_max, _ = bbox_extents(gt_vertices)
    assert np.allclose(out_min, gt_min, atol=1e-5)
    assert np.allclose(out_max, gt_max, atol=1e-5)
    assert len(output_faces) == len(gt_faces), "missing geometry, often caused by skipped instances"
