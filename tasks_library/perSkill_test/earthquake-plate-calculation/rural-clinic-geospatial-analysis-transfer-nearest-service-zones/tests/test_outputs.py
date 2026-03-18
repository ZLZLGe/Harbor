import os

import geopandas as gpd
import pandas as pd


OUTPUT_PATHS = [
    "/root/clinic_service_summary.csv",
    "clinic_service_summary.csv",
]
COUNTIES_FILE = "/root/county_boundaries.geojson"
CLINICS_FILE = "/root/rural_clinics.geojson"
SETTLEMENTS_FILE = "/root/rural_settlements.geojson"
METRIC_CRS = "EPSG:32648"
EXPECTED_COLUMNS = [
    "clinic_id",
    "clinic_name",
    "county_id",
    "county_name",
    "assigned_settlement_count",
    "max_service_distance_km",
]
DISTANCE_TOLERANCE = 0.01


def load_valid_points(points_path: str, counties: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    points = gpd.read_file(points_path)
    points = points[points.geometry.notna()].copy()
    return gpd.sjoin(
        points,
        counties[["county_id", "county_name", "geometry"]],
        how="inner",
        predicate="within",
    ).drop(columns=["index_right"])


def build_expected_summary() -> pd.DataFrame:
    counties = gpd.read_file(COUNTIES_FILE)
    counties = counties[counties.geometry.notna()].copy()

    clinics = load_valid_points(CLINICS_FILE, counties).to_crs(METRIC_CRS)
    settlements = load_valid_points(SETTLEMENTS_FILE, counties).to_crs(METRIC_CRS)

    assignment_rows = []
    for county_id, county_settlements in settlements.groupby("county_id"):
        county_clinics = clinics[clinics["county_id"] == county_id]
        if county_clinics.empty:
            continue

        for _, settlement in county_settlements.iterrows():
            distances_km = county_clinics.geometry.distance(settlement.geometry) / 1000.0
            nearest_idx = distances_km.idxmin()
            nearest_clinic = county_clinics.loc[nearest_idx]
            assignment_rows.append(
                {
                    "clinic_id": nearest_clinic["clinic_id"],
                    "service_distance_km": round(float(distances_km.loc[nearest_idx]), 2),
                }
            )

    clinic_summary = (
        clinics[["clinic_id", "clinic_name", "county_id", "county_name"]]
        .copy()
        .sort_values(["county_id", "clinic_id"])
        .reset_index(drop=True)
    )

    if assignment_rows:
        assignments = pd.DataFrame(assignment_rows)
        aggregated = (
            assignments.groupby("clinic_id", as_index=False)
            .agg(
                assigned_settlement_count=("clinic_id", "size"),
                max_service_distance_km=("service_distance_km", "max"),
            )
        )
    else:
        aggregated = pd.DataFrame(columns=["clinic_id", "assigned_settlement_count", "max_service_distance_km"])

    expected = clinic_summary.merge(aggregated, on="clinic_id", how="left")
    expected["assigned_settlement_count"] = expected["assigned_settlement_count"].fillna(0).astype(int)
    expected["max_service_distance_km"] = expected["max_service_distance_km"].fillna(0.0).round(2)
    return expected[EXPECTED_COLUMNS]


def load_output() -> pd.DataFrame:
    output_path = None
    for candidate in OUTPUT_PATHS:
        if os.path.exists(candidate):
            output_path = candidate
            break

    if output_path is None:
        raise FileNotFoundError(
            "Output file not found. Expected /root/clinic_service_summary.csv"
        )

    return pd.read_csv(output_path)


def test_output_columns_and_row_count():
    actual = load_output()
    expected = build_expected_summary()

    assert list(actual.columns) == EXPECTED_COLUMNS
    assert len(actual) == len(expected)


def test_output_rows_match_expected_summary():
    actual = load_output().copy()
    expected = build_expected_summary().copy()

    actual["assigned_settlement_count"] = actual["assigned_settlement_count"].astype(int)
    expected["assigned_settlement_count"] = expected["assigned_settlement_count"].astype(int)

    assert actual["clinic_id"].tolist() == expected["clinic_id"].tolist()
    assert actual["clinic_name"].tolist() == expected["clinic_name"].tolist()
    assert actual["county_id"].tolist() == expected["county_id"].tolist()
    assert actual["county_name"].tolist() == expected["county_name"].tolist()
    assert actual["assigned_settlement_count"].tolist() == expected["assigned_settlement_count"].tolist()

    for actual_distance, expected_distance in zip(
        actual["max_service_distance_km"],
        expected["max_service_distance_km"],
    ):
        assert abs(actual_distance - expected_distance) <= DISTANCE_TOLERANCE


def test_rows_are_sorted_and_invalid_points_are_excluded():
    actual = load_output()
    sorted_actual = actual.sort_values(["county_id", "clinic_id"]).reset_index(drop=True)

    assert actual.equals(sorted_actual)
    assert "CL99" not in actual["clinic_id"].tolist()
    assert "C103" not in actual["county_id"].tolist()


def test_total_assignments_match_serviceable_settlements():
    actual = load_output()
    expected = build_expected_summary()

    assert actual["assigned_settlement_count"].sum() == expected["assigned_settlement_count"].sum()
    assert actual["assigned_settlement_count"].sum() == 7
