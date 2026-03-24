from pathlib import Path

import numpy as np


OUTPUT_ROOT = Path("/root/output/variants")
PRIMARY_OUTPUT = OUTPUT_ROOT / "west-roof" / "rack.obj"

PANEL_SIZE = np.array([2.2, 0.08, 1.15], dtype=np.float32)

VARIANTS = {
    "west-roof": {
        "origin": np.array([-12.0, 4.2, 6.0], dtype=np.float32),
        "yaw_deg": -32.0,
        "tilt_deg": 26.0,
        "rows": 2,
        "cols": 3,
        "column_gap": 2.55,
        "row_gap": 1.65,
        "panel_centroid_y": 1.9,
        "post_height": 1.55,
    },
    "courtyard-canopy": {
        "origin": np.array([7.5, 5.1, -9.0], dtype=np.float32),
        "yaw_deg": 18.0,
        "tilt_deg": 12.0,
        "rows": 1,
        "cols": 4,
        "column_gap": 2.4,
        "row_gap": 1.8,
        "panel_centroid_y": 2.45,
        "post_height": 2.1,
    },
    "service-shed": {
        "origin": np.array([13.0, 3.8, 11.5], dtype=np.float32),
        "yaw_deg": 74.0,
        "tilt_deg": 34.0,
        "rows": 2,
        "cols": 2,
        "column_gap": 2.7,
        "row_gap": 1.9,
        "panel_centroid_y": 1.75,
        "post_height": 1.4,
    },
}

VERTEX_TOLERANCE = 1e-4


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


def rotation_x(degrees: float) -> np.ndarray:
    radians = np.deg2rad(degrees)
    cosine = np.cos(radians)
    sine = np.sin(radians)
    return np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, cosine, -sine],
            [0.0, sine, cosine],
        ],
        dtype=np.float32,
    )


def rotation_y(degrees: float) -> np.ndarray:
    radians = np.deg2rad(degrees)
    cosine = np.cos(radians)
    sine = np.sin(radians)
    return np.array(
        [
            [cosine, 0.0, sine],
            [0.0, 1.0, 0.0],
            [-sine, 0.0, cosine],
        ],
        dtype=np.float32,
    )


def box_corners(size: np.ndarray) -> np.ndarray:
    half = size / 2.0
    mins = -half
    maxs = half
    return np.array(
        [
            [mins[0], mins[1], mins[2]],
            [mins[0], mins[1], maxs[2]],
            [mins[0], maxs[1], mins[2]],
            [mins[0], maxs[1], maxs[2]],
            [maxs[0], mins[1], mins[2]],
            [maxs[0], mins[1], maxs[2]],
            [maxs[0], maxs[1], mins[2]],
            [maxs[0], maxs[1], maxs[2]],
        ],
        dtype=np.float32,
    )


def centered_offset(index: int, count: int, spacing: float) -> float:
    return (index - (count - 1) / 2.0) * spacing


def array_width(spec: dict) -> float:
    return (spec["cols"] - 1) * spec["column_gap"] + PANEL_SIZE[0]


def array_depth(spec: dict) -> float:
    return (spec["rows"] - 1) * spec["row_gap"] + PANEL_SIZE[2]


def expected_panel_names(spec: dict) -> list[str]:
    return [
        f"panel_r{row + 1}_c{col + 1}"
        for row in range(spec["rows"])
        for col in range(spec["cols"])
    ]


def expected_panel_center(spec: dict, row: int, col: int) -> np.ndarray:
    local = np.array(
        [
            centered_offset(col, spec["cols"], spec["column_gap"]),
            spec["panel_centroid_y"],
            centered_offset(row, spec["rows"], spec["row_gap"]),
        ],
        dtype=np.float32,
    )
    return spec["origin"] + rotation_y(spec["yaw_deg"]) @ local


def expected_panel_bbox(spec: dict, row: int, col: int) -> np.ndarray:
    local_corners = box_corners(PANEL_SIZE) @ rotation_x(-spec["tilt_deg"]).T
    local_corners += np.array(
        [
            centered_offset(col, spec["cols"], spec["column_gap"]),
            spec["panel_centroid_y"],
            centered_offset(row, spec["rows"], spec["row_gap"]),
        ],
        dtype=np.float32,
    )
    world_corners = local_corners @ rotation_y(spec["yaw_deg"]).T + spec["origin"]
    return bbox(world_corners)


def rack_components(spec: dict) -> list[tuple[np.ndarray, np.ndarray, float]]:
    components = []
    rail_length = array_width(spec) - 0.25
    tie_length = rail_length - 0.4
    rail_offsets_z = (-0.34, 0.34)
    rail_group_y = spec["panel_centroid_y"] - 0.24
    tilt = -spec["tilt_deg"]
    tilt_rotation = rotation_x(tilt)

    for row in range(spec["rows"]):
        row_z = centered_offset(row, spec["rows"], spec["row_gap"])

        for offset_z in rail_offsets_z:
            rail_center = tilt_rotation @ np.array([0.0, 0.0, offset_z], dtype=np.float32)
            rail_center += np.array([0.0, rail_group_y, row_z], dtype=np.float32)
            components.append((np.array([rail_length, 0.08, 0.12], dtype=np.float32), rail_center, tilt))

        tie_center = np.array([0.0, 0.32, row_z], dtype=np.float32)
        components.append((np.array([tie_length, 0.1, 0.1], dtype=np.float32), tie_center, 0.0))

        for col in range(spec["cols"]):
            column_x = centered_offset(col, spec["cols"], spec["column_gap"])
            post_center = np.array([column_x, spec["post_height"] / 2.0, row_z], dtype=np.float32)
            foot_center = np.array([column_x, 0.06, row_z], dtype=np.float32)
            components.append((np.array([0.12, spec["post_height"], 0.12], dtype=np.float32), post_center, 0.0))
            components.append((np.array([0.35, 0.12, 0.35], dtype=np.float32), foot_center, 0.0))

    spine_center = np.array([0.0, 0.22, 0.0], dtype=np.float32)
    spine_size = np.array([0.16, 0.16, array_depth(spec) + 0.9], dtype=np.float32)
    components.append((spine_size, spine_center, 0.0))

    return components


def expected_rack_bbox(spec: dict) -> np.ndarray:
    world_corners = []
    yaw_rotation = rotation_y(spec["yaw_deg"])
    for size, center, tilt_deg in rack_components(spec):
        local_corners = box_corners(size) @ rotation_x(tilt_deg).T + center
        world_corners.append(local_corners @ yaw_rotation.T + spec["origin"])
    return bbox(np.concatenate(world_corners, axis=0))


def expected_rack_centroid(spec: dict) -> np.ndarray:
    centers = []
    yaw_rotation = rotation_y(spec["yaw_deg"])
    for _, center, _ in rack_components(spec):
        centers.append(spec["origin"] + yaw_rotation @ center)
    return np.mean(np.stack(centers, axis=0), axis=0)


class TestSolarVariantPack:
    def test_variant_tree_exists(self):
        assert OUTPUT_ROOT.exists()
        assert sorted(p.name for p in OUTPUT_ROOT.iterdir() if p.is_dir()) == sorted(VARIANTS)

    def test_each_variant_has_expected_panel_files(self):
        for variant_name, spec in VARIANTS.items():
            panel_dir = OUTPUT_ROOT / variant_name / "panels"
            assert panel_dir.exists()
            assert sorted(p.name for p in panel_dir.glob("*.obj")) == [
                f"{name}.obj" for name in expected_panel_names(spec)
            ]
            assert (OUTPUT_ROOT / variant_name / "rack.obj").exists()

    def test_panel_exports_have_expected_centroids_and_bboxes(self):
        for variant_name, spec in VARIANTS.items():
            for row in range(spec["rows"]):
                for col in range(spec["cols"]):
                    panel_name = f"panel_r{row + 1}_c{col + 1}"
                    panel_path = OUTPUT_ROOT / variant_name / "panels" / f"{panel_name}.obj"
                    vertices = parse_vertices(panel_path)
                    assert len(vertices) == 36, f"unexpected vertex count for {variant_name}/{panel_name}"

                    centroid = vertices.mean(axis=0)
                    expected_centroid = expected_panel_center(spec, row, col)
                    assert np.allclose(centroid, expected_centroid, atol=VERTEX_TOLERANCE), (
                        f"centroid mismatch for {variant_name}/{panel_name}"
                    )

                    observed_bbox = bbox(vertices)
                    target_bbox = expected_panel_bbox(spec, row, col)
                    assert np.allclose(observed_bbox, target_bbox, atol=VERTEX_TOLERANCE), (
                        f"bbox mismatch for {variant_name}/{panel_name}"
                    )

    def test_rack_exports_have_expected_vertex_counts_and_bboxes(self):
        for variant_name, spec in VARIANTS.items():
            rack_path = OUTPUT_ROOT / variant_name / "rack.obj"
            vertices = parse_vertices(rack_path)
            expected_vertex_count = 36 * len(rack_components(spec))
            assert len(vertices) == expected_vertex_count, (
                f"unexpected rack vertex count for {variant_name}"
            )

            observed_bbox = bbox(vertices)
            target_bbox = expected_rack_bbox(spec)
            assert np.allclose(observed_bbox, target_bbox, atol=VERTEX_TOLERANCE), (
                f"rack bbox mismatch for {variant_name}"
            )

    def test_primary_output_matches_west_roof_rack(self):
        assert PRIMARY_OUTPUT.exists()
        vertices = parse_vertices(PRIMARY_OUTPUT)
        assert len(vertices) == 36 * len(rack_components(VARIANTS["west-roof"]))

        centroid = vertices.mean(axis=0)
        expected_centroid = expected_rack_centroid(VARIANTS["west-roof"])
        assert np.allclose(centroid, expected_centroid, atol=VERTEX_TOLERANCE)
