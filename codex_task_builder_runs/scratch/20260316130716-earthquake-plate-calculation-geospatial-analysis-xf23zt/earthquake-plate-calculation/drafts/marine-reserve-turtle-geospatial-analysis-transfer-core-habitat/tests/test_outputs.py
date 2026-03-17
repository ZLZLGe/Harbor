import csv
import json
import math
import os
import unittest


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
POINTS_FILE = os.environ.get(
    "POINTS_FILE",
    "/root/pelagia_turtle_pings.csv" if os.path.exists("/root/pelagia_turtle_pings.csv")
    else os.path.join(BASE_DIR, "environment", "pelagia_turtle_pings.csv"),
)
POLYGON_FILE = os.environ.get(
    "POLYGON_FILE",
    "/root/pelagia_marine_reserve.geojson" if os.path.exists("/root/pelagia_marine_reserve.geojson")
    else os.path.join(BASE_DIR, "environment", "pelagia_marine_reserve.geojson"),
)
BOUNDARY_FILE = os.environ.get(
    "BOUNDARY_FILE",
    "/root/pelagia_reserve_boundary.geojson" if os.path.exists("/root/pelagia_reserve_boundary.geojson")
    else os.path.join(BASE_DIR, "environment", "pelagia_reserve_boundary.geojson"),
)
OUTPUT_CANDIDATES = ["/root/turtle_core_ping.json", "turtle_core_ping.json"]
METERS_PER_DEGREE = math.pi * 6378137.0 / 180.0
EPS = 1e-12


def project_point(lon, lat):
    return lon * METERS_PER_DEGREE, lat * METERS_PER_DEGREE


def point_on_segment(point, start, end):
    px, py = point
    x1, y1 = start
    x2, y2 = end

    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > EPS:
        return False

    dot = (px - x1) * (px - x2) + (py - y1) * (py - y2)
    return dot <= EPS


def point_in_polygon_strict(point, polygon):
    for start, end in zip(polygon, polygon[1:]):
        if point_on_segment(point, start, end):
            return False

    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:]):
        if (y1 > y) == (y2 > y):
            continue
        xinters = (x2 - x1) * (y - y1) / (y2 - y1) + x1
        if x < xinters:
            inside = not inside
    return inside


def point_to_segment_distance(point_xy, segment):
    (x1, y1), (x2, y2) = segment
    px, py = point_xy
    dx = x2 - x1
    dy = y2 - y1
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0.0:
        return math.hypot(px - x1, py - y1)

    t = ((px - x1) * dx + (py - y1) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def load_polygon():
    with open(POLYGON_FILE, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data["features"][0]["geometry"]["coordinates"][0]


def load_boundary_segments():
    with open(BOUNDARY_FILE, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    segments = []
    for feature in data["features"]:
        geometry = feature["geometry"]
        if geometry["type"] == "LineString":
            coords = geometry["coordinates"]
            segments.extend(zip(coords, coords[1:]))
        elif geometry["type"] == "MultiLineString":
            for line in geometry["coordinates"]:
                segments.extend(zip(line, line[1:]))
        else:
            raise ValueError(f"Unsupported geometry type: {geometry['type']}")
    return [(project_point(*start), project_point(*end)) for start, end in segments]


def load_points():
    with open(POINTS_FILE, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(
                {
                    "tag_id": row["tag_id"],
                    "observed_at": row["observed_at"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            )
    return rows


def compute_expected_result():
    polygon = load_polygon()
    boundary_segments = load_boundary_segments()

    best_row = None
    best_distance_km = -1.0

    for row in load_points():
        point_lonlat = (row["longitude"], row["latitude"])
        if not point_in_polygon_strict(point_lonlat, polygon):
            continue

        point_xy = project_point(*point_lonlat)
        distance_km = min(
            point_to_segment_distance(point_xy, segment) for segment in boundary_segments
        ) / 1000.0

        if distance_km > best_distance_km:
            best_row = row
            best_distance_km = distance_km

    if best_row is None:
        raise AssertionError("Input assets produced no interior turtle observation.")

    return {
        "tag_id": best_row["tag_id"],
        "observed_at": best_row["observed_at"],
        "latitude": best_row["latitude"],
        "longitude": best_row["longitude"],
        "distance_km": round(best_distance_km, 2),
    }


class TestTurtleCorePing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        answer_path = None
        for candidate in OUTPUT_CANDIDATES:
            if os.path.exists(candidate):
                answer_path = candidate
                break

        if answer_path is None:
            raise FileNotFoundError("Missing /root/turtle_core_ping.json")

        with open(answer_path, "r", encoding="utf-8") as handle:
            cls.result = json.load(handle)

        cls.expected = compute_expected_result()

    def test_output_structure(self):
        self.assertEqual(
            set(self.result.keys()),
            {"tag_id", "observed_at", "latitude", "longitude", "distance_km"},
        )

    def test_matches_recomputed_winner(self):
        self.assertEqual(self.result["tag_id"], self.expected["tag_id"])
        self.assertEqual(self.result["observed_at"], self.expected["observed_at"])
        self.assertAlmostEqual(self.result["latitude"], self.expected["latitude"], places=6)
        self.assertAlmostEqual(self.result["longitude"], self.expected["longitude"], places=6)
        self.assertAlmostEqual(self.result["distance_km"], self.expected["distance_km"], places=2)

    def test_winner_is_strictly_inside_reserve(self):
        polygon = load_polygon()
        point = (self.result["longitude"], self.result["latitude"])
        self.assertTrue(point_in_polygon_strict(point, polygon))

    def test_distance_is_positive_and_dominant(self):
        expected = compute_expected_result()
        self.assertGreater(self.result["distance_km"], 0.0)
        self.assertAlmostEqual(self.result["distance_km"], expected["distance_km"], places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
