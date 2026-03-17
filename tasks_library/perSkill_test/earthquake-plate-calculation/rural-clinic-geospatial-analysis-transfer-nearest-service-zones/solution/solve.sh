#!/bin/bash
set -euo pipefail

python3 <<'PY'
import pandas as pd
import geopandas as gpd

COUNTIES_FILE = "/root/county_boundaries.geojson"
CLINICS_FILE = "/root/rural_clinics.geojson"
SETTLEMENTS_FILE = "/root/rural_settlements.geojson"
OUTPUT_FILE = "/root/clinic_service_summary.csv"
METRIC_CRS = "EPSG:32648"


def load_valid_points(points_path: str, counties: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    points = gpd.read_file(points_path)
    points = points[points.geometry.notna()].copy()
    return gpd.sjoin(
        points,
        counties[["county_id", "county_name", "geometry"]],
        how="inner",
        predicate="within",
    ).drop(columns=["index_right"])


def assign_settlements(
    settlements: gpd.GeoDataFrame,
    clinics: gpd.GeoDataFrame,
) -> pd.DataFrame:
    assignments = []

    for county_id, county_settlements in settlements.groupby("county_id"):
        county_clinics = clinics[clinics["county_id"] == county_id]
        if county_clinics.empty:
            continue

        for _, settlement in county_settlements.iterrows():
            distances_km = county_clinics.geometry.distance(settlement.geometry) / 1000.0
            nearest_idx = distances_km.idxmin()
            nearest_clinic = county_clinics.loc[nearest_idx]

            assignments.append(
                {
                    "clinic_id": nearest_clinic["clinic_id"],
                    "service_distance_km": round(float(distances_km.loc[nearest_idx]), 2),
                }
            )

    return pd.DataFrame(assignments)


def main():
    counties = gpd.read_file(COUNTIES_FILE)
    counties = counties[counties.geometry.notna()].copy()

    clinics = load_valid_points(CLINICS_FILE, counties)
    settlements = load_valid_points(SETTLEMENTS_FILE, counties)

    clinics_proj = clinics.to_crs(METRIC_CRS)
    settlements_proj = settlements.to_crs(METRIC_CRS)

    assignments = assign_settlements(settlements_proj, clinics_proj)

    clinic_summary = (
        clinics_proj[["clinic_id", "clinic_name", "county_id", "county_name"]]
        .copy()
        .sort_values(["county_id", "clinic_id"])
        .reset_index(drop=True)
    )

    if assignments.empty:
        aggregated = pd.DataFrame(columns=["clinic_id", "assigned_settlement_count", "max_service_distance_km"])
    else:
        aggregated = (
            assignments.groupby("clinic_id", as_index=False)
            .agg(
                assigned_settlement_count=("clinic_id", "size"),
                max_service_distance_km=("service_distance_km", "max"),
            )
        )

    result = clinic_summary.merge(aggregated, on="clinic_id", how="left")
    result["assigned_settlement_count"] = result["assigned_settlement_count"].fillna(0).astype(int)
    result["max_service_distance_km"] = result["max_service_distance_km"].fillna(0.0).round(2)
    result = result[
        [
            "clinic_id",
            "clinic_name",
            "county_id",
            "county_name",
            "assigned_settlement_count",
            "max_service_distance_km",
        ]
    ]

    result.to_csv(OUTPUT_FILE, index=False, float_format="%.2f")


if __name__ == "__main__":
    main()
PY
