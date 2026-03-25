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


class TestLoadingYard:
    OUTPUT_PATH = "/root/output/loading_yard.obj"
    GROUND_TRUTH_PATH = "/root/ground_truth/loading_yard.obj"
    THRESHOLD = 1e-5

    def test_output_exists(self):
        assert os.path.exists(self.OUTPUT_PATH)
        assert os.path.getsize(self.OUTPUT_PATH) > 0

    def test_vertex_and_face_counts_match_ground_truth(self):
        output_vertices, output_faces = parse_obj(self.OUTPUT_PATH)
        expected_vertices, expected_faces = parse_obj(self.GROUND_TRUTH_PATH)
        assert len(output_vertices) == len(expected_vertices)
        assert output_faces == expected_faces

    def test_geometry_matches_ground_truth(self):
        output_vertices, _ = parse_obj(self.OUTPUT_PATH)
        expected_vertices, _ = parse_obj(self.GROUND_TRUTH_PATH)
        distance = chamfer_distance(output_vertices, expected_vertices)
        assert distance < self.THRESHOLD, distance
