import os
import numpy as np


def parse_obj(filepath):
    vertices = []
    face_count = 0
    with open(filepath, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z = line.strip().split()[:4]
                vertices.append([float(x), float(y), float(z)])
            elif line.startswith("f "):
                face_count += 1
    return np.array(vertices), face_count


def chamfer_distance(points_a, points_b):
    distances_a = []
    for point in points_a:
        distances_a.append(np.min(np.linalg.norm(points_b - point, axis=1)))

    distances_b = []
    for point in points_b:
        distances_b.append(np.min(np.linalg.norm(points_a - point, axis=1)))

    return float(np.mean(distances_a) + np.mean(distances_b))


class TestModularDisplay:
    OUTPUT_PATH = "/root/output/modular_display.obj"
    GROUND_TRUTH_PATH = "/root/ground_truth/modular_display.obj"
    THRESHOLD = 1e-5

    def test_output_exists(self):
        assert os.path.exists(self.OUTPUT_PATH)
        assert os.path.getsize(self.OUTPUT_PATH) > 0

    def test_geometry_matches_ground_truth(self):
        output_vertices, output_faces = parse_obj(self.OUTPUT_PATH)
        expected_vertices, expected_faces = parse_obj(self.GROUND_TRUTH_PATH)
        assert output_faces == expected_faces
        distance = chamfer_distance(output_vertices, expected_vertices)
        assert distance < self.THRESHOLD, distance

    def test_extent_matches_ground_truth(self):
        output_vertices, _ = parse_obj(self.OUTPUT_PATH)
        expected_vertices, _ = parse_obj(self.GROUND_TRUTH_PATH)
        output_span = output_vertices.max(axis=0) - output_vertices.min(axis=0)
        expected_span = expected_vertices.max(axis=0) - expected_vertices.min(axis=0)
        assert np.allclose(output_span, expected_span, atol=1e-5)
