#!/bin/bash
set -e

python3 <<'PY'
import json

import geopandas as gpd


ROUTES_FILE = "/root/ferry_routes.geojson"
ZONES_FILE = "/root/seasonal_slow_zones.geojson"
OUTPUT_FILE = "/root/ferry_slowzone_overlap.json"
METRIC_CRS = "EPSG:32648"


def main():
    routes = gpd.read_file(ROUTES_FILE)
    zones = gpd.read_file(ZONES_FILE)

    if routes.crs is None:
        routes = routes.set_crs("EPSG:4326")
    if zones.crs is None:
        zones = zones.set_crs("EPSG:4326")

    spring_zones = zones[zones["season"] == "spring"].copy()
    spring_union = spring_zones.geometry.unary_union

    routes_proj = routes.to_crs(METRIC_CRS)
    spring_union_proj = (
        gpd.GeoSeries([spring_union], crs=routes.crs).to_crs(METRIC_CRS).iloc[0]
    )

    best = None

    for idx, route in routes.iterrows():
        route_geom = route.geometry
        route_geom_proj = routes_proj.loc[idx, "geometry"]
        overlap_length_km = route_geom_proj.intersection(spring_union_proj).length / 1000.0

        zone_ids = sorted(
            spring_zones.loc[spring_zones.geometry.intersects(route_geom), "zone_id"]
            .dropna()
            .unique()
            .tolist()
        )

        candidate = {
            "season": "spring",
            "route_id": route["route_id"],
            "route_name": route["route_name"],
            "operator": route["operator"],
            "intersecting_zone_ids": zone_ids,
            "overlap_length_km": round(overlap_length_km, 2),
        }

        if best is None:
            best = (overlap_length_km, candidate)
            continue

        best_length, best_candidate = best
        if overlap_length_km > best_length + 1e-9 or (
            abs(overlap_length_km - best_length) <= 1e-9
            and candidate["route_id"] < best_candidate["route_id"]
        ):
            best = (overlap_length_km, candidate)

    if best is None:
        raise RuntimeError("No routes found in input data.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(best[1], handle, indent=2)


if __name__ == "__main__":
    main()
PY
