#!/bin/bash
set -e

python3 <<'PY'
import csv
import json
import math
import os

INPUT_POINTS = os.environ.get("INPUT_POINTS", "/root/pelagia_turtle_pings.csv")
INPUT_POLYGON = os.environ.get("INPUT_POLYGON", "/root/pelagia_marine_reserve.geojson")
INPUT_BOUNDARY = os.environ.get("INPUT_BOUNDARY", "/root/pelagia_reserve_boundary.geojson")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/turtle_core_ping.json")
METERS_PER_DEGREE = math.pi * 6378137.0 / 180.0
EPS = 1e-12


def project_point(lon, lat):
    return lon * METERS_PER_DEGREE, lat * METERS_PER_DEGREE


def load_points():
    with open(INPUT_POINTS, "r", encoding="utf-8", newline="") as handle:
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


def load_polygon():
    with open(INPUT_POLYGON, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data["features"][0]["geometry"]["coordinates"][0]


def load_boundary_segments():
    with open(INPUT_BOUNDARY, "r", encoding="utf-8") as handle:
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
    return segments


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
        intersects = ((y1 > y) != (y2 > y))
        if not intersects:
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


def main():
    polygon = load_polygon()
    boundary_segments = [
        (project_point(*start), project_point(*end))
        for start, end in load_boundary_segments()
    ]

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
        raise RuntimeError("No turtle observations found strictly inside the reserve polygon.")

    result = {
        "tag_id": best_row["tag_id"],
        "observed_at": best_row["observed_at"],
        "latitude": best_row["latitude"],
        "longitude": best_row["longitude"],
        "distance_km": round(best_distance_km, 2),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
PY
