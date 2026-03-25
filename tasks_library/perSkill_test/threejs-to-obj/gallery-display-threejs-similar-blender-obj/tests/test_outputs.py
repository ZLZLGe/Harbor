import json
import os

import numpy as np


OUTPUT_OBJ = "/root/output/display.obj"
GROUND_TRUTH = "/root/ground_truth/display_points.json"


def parse_obj(path):
    vertices = []
    faces = []

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                vertices.append([float(x), float(y), float(z)])
            elif line.startswith("f "):
                refs = []
                for token in line.split()[1:]:
                    vertex_index = token.split("/")[0]
                    refs.append(int(vertex_index))
                faces.append(refs)

    return np.asarray(vertices, dtype=float), faces


def canonicalize(points):
    rounded = np.round(points, 6)
    unique = np.unique(rounded, axis=0)
    order = np.lexsort((unique[:, 2], unique[:, 1], unique[:, 0]))
    return unique[order]


def test_output_exists():
    assert os.path.exists(OUTPUT_OBJ), f"missing output file: {OUTPUT_OBJ}"
    assert os.path.getsize(OUTPUT_OBJ) > 0, "output OBJ is empty"


def test_obj_contains_valid_geometry():
    vertices, faces = parse_obj(OUTPUT_OBJ)

    assert len(vertices) > 0, "OBJ has no vertices"
    assert len(faces) > 0, "OBJ has no faces"

    for face in faces:
        assert len(face) >= 3, f"face has fewer than 3 vertices: {face}"
        for vertex_index in face:
            assert 1 <= vertex_index <= len(vertices), (
                f"face index {vertex_index} is outside vertex range 1..{len(vertices)}"
            )


def test_unique_vertex_point_set_matches_reference():
    assert os.path.exists(GROUND_TRUTH), f"missing reference data: {GROUND_TRUTH}"

    output_vertices, _ = parse_obj(OUTPUT_OBJ)
    with open(GROUND_TRUTH, "r", encoding="utf-8") as handle:
        reference_points = np.asarray(json.load(handle)["points"], dtype=float)

    output_points = canonicalize(output_vertices)
    reference_points = canonicalize(reference_points)

    assert output_points.shape == reference_points.shape, (
        "unique vertex count mismatch: "
        f"output={output_points.shape[0]} reference={reference_points.shape[0]}"
    )
    assert np.allclose(output_points, reference_points, atol=1e-6), (
        "unique vertex point set does not match the visible baked assembly"
    )
