#!/bin/bash
set -e

python3 <<'PY'
import csv
import json
import math
import os

ALERT_FILE = os.environ.get("ALERT_FILE", "/root/heatwave_alert_zones.geojson")
COMMUNITY_FILE = os.environ.get("COMMUNITY_FILE", "/root/community_centers.csv")
COOLING_FILE = os.environ.get("COOLING_FILE", "/root/cooling_centers.csv")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/cooling_access_gap.json")
EARTH_RADIUS_M = 6378137.0
EPS = 1e-12


def project_web_mercator(lon, lat):
    lat = max(min(lat, 89.5), -89.5)
    lon_rad = math.radians(lon)
    lat_rad = math.radians(lat)
    x = EARTH_RADIUS_M * lon_rad
    y = EARTH_RADIUS_M * math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0))
    return x, y


def euclidean_distance_km(point_a, point_b):
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

    zones = []
    for feature in data["features"]:
        zones.append(
            {
                "alert_zone_id": feature["properties"]["alert_zone_id"],
                "polygon": feature["geometry"]["coordinates"][0],
            }
        )
    return zones


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


def select_alert_zone(point, zones):
    matches = []
    for zone in zones:
        if point_in_polygon_strict(point, zone["polygon"]):
            matches.append(zone["alert_zone_id"])
    if not matches:
        return None
    return sorted(matches)[0]


def nearest_cooling_center(community_point, cooling_centers):
    best = None
    best_distance = None
    for center in cooling_centers:
        distance_km = euclidean_distance_km(
            community_point,
            (center["longitude"], center["latitude"]),
        )
        candidate = (distance_km, center["cooling_center_id"])
        if best is None or candidate < (best_distance, best["cooling_center_id"]):
            best = center
            best_distance = distance_km
    return best, best_distance


def main():
    zones = load_alert_zones()
    communities = load_csv(COMMUNITY_FILE, "community_center_id")
    cooling_centers = load_csv(COOLING_FILE, "cooling_center_id")

    best_result = None
    best_distance = -1.0

    for community in communities:
        point = (community["longitude"], community["latitude"])
        alert_zone_id = select_alert_zone(point, zones)
        if alert_zone_id is None:
            continue

        nearest_center, nearest_distance = nearest_cooling_center(point, cooling_centers)
        if nearest_distance > best_distance:
            best_distance = nearest_distance
            best_result = {
                "alert_zone_id": alert_zone_id,
                "community_center_id": community["community_center_id"],
                "nearest_cooling_center_id": nearest_center["cooling_center_id"],
                "community_latitude": community["latitude"],
                "community_longitude": community["longitude"],
                "nearest_distance_km": round(nearest_distance, 2),
            }

    if best_result is None:
        raise RuntimeError("No community centers were found inside any heatwave alert zone.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(best_result, handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
PY
