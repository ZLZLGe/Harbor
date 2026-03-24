import hashlib
import json
import os

import numpy as np


OUTPUT_PATH = "/root/output/lattice.obj"
SIGNATURE_PATH = "/root/ground_truth/lattice_signature.json"


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


def bbox(points):
    minimum = points.min(axis=0)
    maximum = points.max(axis=0)
    return minimum, maximum, maximum - minimum


def centroid(points):
    return points.mean(axis=0)


def vertex_digest(points):
    ordered = sorted(
        f"{point[0]:.6f},{point[1]:.6f},{point[2]:.6f}"
        for point in points
    )
    return hashlib.sha256("\n".join(ordered).encode("utf-8")).hexdigest()


def load_signature():
    with open(SIGNATURE_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_output_exists():
    assert os.path.exists(OUTPUT_PATH), f"missing output: {OUTPUT_PATH}"
    assert os.path.getsize(OUTPUT_PATH) > 0, "output OBJ is empty"


def test_obj_contains_nontrivial_geometry():
    vertices, faces = parse_obj(OUTPUT_PATH)
    assert len(vertices) > 10000, "expected a full lattice export"
    assert len(faces) > 3000, "expected faces in the OBJ export"


def test_vertex_signature_matches_ground_truth():
    assert os.path.exists(SIGNATURE_PATH), f"missing signature data: {SIGNATURE_PATH}"

    vertices, faces = parse_obj(OUTPUT_PATH)
    signature = load_signature()

    assert len(vertices) == signature["vertex_count"], "vertex count mismatch"
    assert len(faces) == signature["face_count"], "face count mismatch"

    out_min, out_max, out_extents = bbox(vertices)
    assert np.allclose(out_min, signature["bbox_min"], atol=1e-5)
    assert np.allclose(out_max, signature["bbox_max"], atol=1e-5)
    assert np.allclose(out_extents, signature["bbox_extents"], atol=1e-5)
    assert np.allclose(centroid(vertices), signature["centroid"], atol=1e-5)
    assert vertex_digest(vertices) == signature["vertex_digest"], "vertex signature mismatch"


def test_export_is_blender_z_up():
    vertices, _ = parse_obj(OUTPUT_PATH)
    _, _, extents = bbox(vertices)

    assert extents[2] > extents[1], (
        "after the required X rotation, the lattice height should be expressed on Blender Z"
    )
    assert extents[2] > 5.0, "the rotated export should span a meaningful distance on Z"
