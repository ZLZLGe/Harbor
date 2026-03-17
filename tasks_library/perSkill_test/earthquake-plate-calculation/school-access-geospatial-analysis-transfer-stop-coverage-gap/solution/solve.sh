#!/bin/bash
set -e

python3 <<'EOF'
import json
import pandas as pd
import geopandas as gpd

SCHOOLS_FILE = "/root/school_locations.csv"
STOPS_FILE = "/root/bus_stops.csv"
OUTPUT_FILE = "/root/school_stop_coverage.json"
METRIC_CRS = "EPSG:32618"
BUFFER_RADIUS_M = 400
MINIMUM_STOP_TARGET = 3


def build_points(frame: pd.DataFrame, x_col: str, y_col: str) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        frame.copy(),
        geometry=gpd.points_from_xy(frame[x_col], frame[y_col]),
        crs=METRIC_CRS,
    )


def main() -> None:
    schools_df = pd.read_csv(SCHOOLS_FILE)
    stops_df = pd.read_csv(STOPS_FILE)

    schools = build_points(schools_df, "easting_m", "northing_m")
    stops = build_points(stops_df, "easting_m", "northing_m")

    school_buffers = schools[["school_id", "school_name", "geometry"]].copy()
    school_buffers["geometry"] = school_buffers.geometry.buffer(BUFFER_RADIUS_M)

    joined = gpd.sjoin(stops, school_buffers, how="inner", predicate="within")
    stop_counts = joined.groupby("school_id").size()

    schools["reachable_stop_count"] = (
        schools["school_id"].map(stop_counts).fillna(0).astype(int)
    )
    schools["coverage_gap"] = (
        MINIMUM_STOP_TARGET - schools["reachable_stop_count"]
    ).clip(lower=0)

    school_audit = (
        schools[["school_id", "school_name", "reachable_stop_count", "coverage_gap"]]
        .sort_values(
            by=["coverage_gap", "reachable_stop_count", "school_id"],
            ascending=[False, True, True],
        )
        .to_dict(orient="records")
    )

    result = {
        "metric_crs": METRIC_CRS,
        "buffer_radius_m": BUFFER_RADIUS_M,
        "minimum_stop_target": MINIMUM_STOP_TARGET,
        "worst_school": school_audit[0],
        "school_audit": school_audit,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
EOF
