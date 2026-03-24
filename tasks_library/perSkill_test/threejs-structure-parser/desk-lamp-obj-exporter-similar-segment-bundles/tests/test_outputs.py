from pathlib import Path

import numpy as np


OUTPUT_DIR = Path("/root/output")
GROUND_TRUTH_DIR = Path("/root/ground_truth")
EXPECTED_SEGMENTS = sorted(["lamp_base", "lower_arm", "upper_arm", "lamp_head"])
PRIMARY_OUTPUT = OUTPUT_DIR / "links" / "lamp_head.obj"
PRIMARY_GT = GROUND_TRUTH_DIR / "links" / "lamp_head.obj"
CHAMFER_THRESHOLD = 2e-4


def parse_vertices(path: Path) -> np.ndarray:
    vertices = []
    with path.open("r") as handle:
        for line in handle:
            if line.startswith("v "):
                _, x, y, z = line.strip().split()[:4]
                vertices.append([float(x), float(y), float(z)])
    return np.asarray(vertices, dtype=np.float32)


def bbox(points: np.ndarray) -> np.ndarray:
    return np.stack([points.min(axis=0), points.max(axis=0)], axis=0)


def sorted_obj_names(folder: Path):
    return sorted(p.name for p in folder.glob("*.obj"))


def chamfer_distance(points1: np.ndarray, points2: np.ndarray) -> float:
    if len(points1) == 0 or len(points2) == 0:
        return float("inf")
    diff = points1[:, None, :] - points2[None, :, :]
    dist = np.linalg.norm(diff, axis=2)
    return float(dist.min(axis=1).mean() + dist.min(axis=0).mean())


class TestDeskLampExports:
    def test_output_tree_exists(self):
        assert (OUTPUT_DIR / "part_meshes").exists()
        assert (OUTPUT_DIR / "links").exists()

    def test_segment_directories_and_link_files_match(self):
        part_root = OUTPUT_DIR / "part_meshes"
        out_segments = sorted(p.name for p in part_root.iterdir() if p.is_dir())
        assert out_segments == EXPECTED_SEGMENTS

        link_files = sorted_obj_names(OUTPUT_DIR / "links")
        assert link_files == [f"{segment}.obj" for segment in EXPECTED_SEGMENTS]

    def test_mesh_file_names_match_ground_truth(self):
        for segment in EXPECTED_SEGMENTS:
            out_dir = OUTPUT_DIR / "part_meshes" / segment
            gt_dir = GROUND_TRUTH_DIR / "part_meshes" / segment
            assert sorted_obj_names(out_dir) == sorted_obj_names(gt_dir)

    def test_every_obj_has_expected_vertex_count_and_bbox(self):
        for gt_file in GROUND_TRUTH_DIR.rglob("*.obj"):
            relative = gt_file.relative_to(GROUND_TRUTH_DIR)
            out_file = OUTPUT_DIR / relative
            assert out_file.exists(), f"missing output {relative}"

            gt_vertices = parse_vertices(gt_file)
            out_vertices = parse_vertices(out_file)
            assert len(out_vertices) == len(gt_vertices), f"vertex count mismatch for {relative}"

            gt_bbox = bbox(gt_vertices)
            out_bbox = bbox(out_vertices)
            assert np.allclose(out_bbox, gt_bbox, atol=1e-5), f"bbox mismatch for {relative}"

    def test_primary_output_geometry_matches(self):
        assert PRIMARY_OUTPUT.exists()
        assert PRIMARY_GT.exists()

        out_vertices = parse_vertices(PRIMARY_OUTPUT)
        gt_vertices = parse_vertices(PRIMARY_GT)
        assert len(out_vertices) > 0
        assert len(gt_vertices) > 0

        distance = chamfer_distance(out_vertices, gt_vertices)
        assert distance < CHAMFER_THRESHOLD
