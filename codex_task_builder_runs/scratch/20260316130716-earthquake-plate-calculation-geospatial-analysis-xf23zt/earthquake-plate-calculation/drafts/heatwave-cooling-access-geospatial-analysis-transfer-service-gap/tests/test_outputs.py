import csv
import json
import math
import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ALERT_FILE = os.environ.get(
    "ALERT_FILE",
    "/root/heatwave_alert_zones.geojson"
    if os.path.exists("/root/heatwave_alert_zones.geojson")
    else os.path.join(BASE_DIR, "environment", "heatwave_alert_zones.geojson"),
)
COMMUNITY_FILE = os.environ.get(
    "COMMUNITY_FILE",
    "/root/community_centers.csv"
    if os.path.exists("/root/community_centers.csv")
    else os.path.join(BASE_DIR, "environment", "community_centers.csv"),
)
COOLING_FILE = os.environ.get(
    "COOLING_FILE",
    "/root/cooling_centers.csv"
    if os.path.exists("/root/cooling_centers.csv")
    else os.path.join(BASE_DIR, "environment", "cooling_centers.csv"),
)
OUTPUT_CANDIDATES = ["/root/cooling_access_gap.json", "cooling_access_gap.json"]
EARTH_RADIUS_M = 6378137.0
EPS = 1e-12


def project_web_mercator(lon, lat):
    lat = max(min(lat, 89.5), -89.5)
    lon_rad = math.radians(lon)
    lat_rad = math.radians(lat)
    x = EARTH_RADIUS_M * lon_rad
    y = EARTH_RADIUS_M * math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0))
    return x, y


def distance_km(point_a, point_b):
    ax, ay = project_web_mercator(point_a[0], point_a[1])
    bx, by = project_web_mercator(point_b[0], point_b[1])
    return math.hypot(ax - bx, ay - by) / 1000.0


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
        intersection_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
        if x < intersection_x:
            inside = not inside
    return inside


def load_alert_zones():
    with open(ALERT_FILE, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return [
        {
            "alert_zone_id": feature["properties"]["alert_zone_id"],
            "polygon": feature["geometry"]["coordinates"][0],
        }
        for feature in data["features"]
    ]


def load_csv(path, id_field):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(
                {
                    id_field: row[id_field],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            )
    return rows


def pick_alert_zone(point, zones):
    matches = [
        zone["alert_zone_id"]
        for zone in zones
        if point_in_polygon_strict(point, zone["polygon"])
    ]
    if not matches:
        return None
    return sorted(matches)[0]


def compute_expected():
    zones = load_alert_zones()
    communities = load_csv(COMMUNITY_FILE, "community_center_id")
    cooling_centers = load_csv(COOLING_FILE, "cooling_center_id")

    best = None
    best_distance = -1.0

    for community in communities:
        point = (community["longitude"], community["latitude"])
        alert_zone_id = pick_alert_zone(point, zones)
        if alert_zone_id is None:
            continue

        nearest_distance = None
        nearest_cooling_center_id = None
        for center in cooling_centers:
            candidate_distance = distance_km(
                point,
                (center["longitude"], center["latitude"]),
            )
            candidate_key = (candidate_distance, center["cooling_center_id"])
            if nearest_distance is None or candidate_key < (
                nearest_distance,
                nearest_cooling_center_id,
            ):
                nearest_distance = candidate_distance
                nearest_cooling_center_id = center["cooling_center_id"]

        candidate = {
            "alert_zone_id": alert_zone_id,
            "community_center_id": community["community_center_id"],
            "nearest_cooling_center_id": nearest_cooling_center_id,
            "community_latitude": community["latitude"],
            "community_longitude": community["longitude"],
            "nearest_distance_km": round(nearest_distance, 2),
        }

        if nearest_distance > best_distance:
            best_distance = nearest_distance
            best = candidate

    if best is None:
        raise AssertionError("No eligible community center found inside any alert zone.")
    return best


def load_result():
    for candidate in OUTPUT_CANDIDATES:
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as handle:
                return json.load(handle)
    raise FileNotFoundError("Missing /root/cooling_access_gap.json")


def test_output_structure():
    result = load_result()
    assert set(result.keys()) == {
        "alert_zone_id",
        "community_center_id",
        "nearest_cooling_center_id",
        "community_latitude",
        "community_longitude",
        "nearest_distance_km",
    }


def test_matches_recomputed_gap_winner():
    result = load_result()
    expected = compute_expected()
    assert result["alert_zone_id"] == expected["alert_zone_id"]
    assert result["community_center_id"] == expected["community_center_id"]
    assert result["nearest_cooling_center_id"] == expected["nearest_cooling_center_id"]
    assert abs(result["community_latitude"] - expected["community_latitude"]) <= 1e-9
    assert abs(result["community_longitude"] - expected["community_longitude"]) <= 1e-9
    assert abs(result["nearest_distance_km"] - expected["nearest_distance_km"]) <= 0.01


def test_winner_is_inside_alert_zone():
    result = load_result()
    zones = load_alert_zones()
    point = (result["community_longitude"], result["community_latitude"])
    matching_zones = [
        zone["alert_zone_id"]
        for zone in zones
        if point_in_polygon_strict(point, zone["polygon"])
    ]
    assert matching_zones
    assert result["alert_zone_id"] == sorted(matching_zones)[0]


def test_reported_cooling_center_is_actually_nearest():
    result = load_result()
    cooling_centers = load_csv(COOLING_FILE, "cooling_center_id")
    point = (result["community_longitude"], result["community_latitude"])

    distances = sorted(
        (
            distance_km(point, (center["longitude"], center["latitude"])),
            center["cooling_center_id"],
        )
        for center in cooling_centers
    )
    nearest_distance, nearest_id = distances[0]

    assert result["nearest_cooling_center_id"] == nearest_id
    assert abs(result["nearest_distance_km"] - round(nearest_distance, 2)) <= 0.01
