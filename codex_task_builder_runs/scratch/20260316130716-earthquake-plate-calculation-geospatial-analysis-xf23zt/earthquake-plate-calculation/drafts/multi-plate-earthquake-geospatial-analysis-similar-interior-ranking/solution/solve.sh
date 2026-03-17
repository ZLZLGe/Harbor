#!/bin/bash
set -e

python3 <<'PY'
import json
from datetime import datetime

import geopandas as gpd
from shapely.geometry import Point

EARTHQUAKES_FILE = "/root/earthquakes_2024.json"
PLATES_FILE = "/root/PB2002_plates.json"
BOUNDARIES_FILE = "/root/PB2002_boundaries.json"
OUTPUT_FILE = "/root/plate_interior_winner.json"
METRIC_CRS = "EPSG:4087"

TARGET_PLATES = [
    ("PA", "Pacific"),
    ("NZ", "Nazca"),
    ("PS", "Philippine Sea"),
    ("CO", "Cocos"),
]


def load_earthquakes():
    with open(EARTHQUAKES_FILE, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    records = []
    for feature in raw["features"]:
        props = feature["properties"]
        lon, lat, depth = feature["geometry"]["coordinates"]
        records.append(
            {
                "id": feature["id"],
                "place": props["place"],
                "time_ms": props["time"],
                "magnitude": props["mag"],
                "longitude": lon,
                "latitude": lat,
                "depth": depth,
            }
        )
    return records


def format_time(epoch_ms):
    return datetime.utcfromtimestamp(epoch_ms / 1000.0).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    earthquakes = load_earthquakes()
    plates = gpd.read_file(PLATES_FILE)
    boundaries = gpd.read_file(BOUNDARIES_FILE)

    eq_gdf = gpd.GeoDataFrame(
        earthquakes,
        geometry=[Point(eq["longitude"], eq["latitude"]) for eq in earthquakes],
        crs="EPSG:4326",
    )

    ranking_rows = []

    for plate_code, plate_name in TARGET_PLATES:
        plate_geom = plates.loc[plates["Code"] == plate_code, "geometry"].unary_union
        inside = eq_gdf[eq_gdf.within(plate_geom)].copy()
        if inside.empty:
            raise RuntimeError(f"No earthquakes found within plate {plate_name}")

        boundary_geom = (
            boundaries[
                (boundaries["PlateA"] == plate_code) | (boundaries["PlateB"] == plate_code)
            ]
            .to_crs(METRIC_CRS)
            .geometry.unary_union
        )

        inside_proj = inside.to_crs(METRIC_CRS)
        inside["distance_km"] = inside_proj.geometry.distance(boundary_geom) / 1000.0

        winner = inside.nlargest(1, "distance_km").iloc[0]
        ranking_rows.append(
            {
                "plate_code": plate_code,
                "plate_name": plate_name,
                "earthquake_count_inside": int(len(inside)),
                "id": winner["id"],
                "place": winner["place"],
                "time": format_time(winner["time_ms"]),
                "magnitude": float(winner["magnitude"]),
                "latitude": float(winner["latitude"]),
                "longitude": float(winner["longitude"]),
                "distance_km": round(float(winner["distance_km"]), 2),
            }
        )

    ranking_rows.sort(key=lambda row: row["distance_km"], reverse=True)
    champion = ranking_rows[0]

    result = {
        "winning_plate": {
            "plate_code": champion["plate_code"],
            "plate_name": champion["plate_name"],
        },
        "winning_earthquake": {
            "id": champion["id"],
            "place": champion["place"],
            "time": champion["time"],
            "magnitude": champion["magnitude"],
            "latitude": champion["latitude"],
            "longitude": champion["longitude"],
        },
        "winning_distance_km": champion["distance_km"],
        "plate_rankings": ranking_rows,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
PY
