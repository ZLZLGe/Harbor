import json
import math
from pathlib import Path

import pandas as pd

OUTPUT_PATH = Path("/root/volcano_swarm_events.geojson")
EXPECTED_PATH = Path("/tests/expected_events.csv")
REQUIRED_PROPERTIES = {
    "time",
    "depth_km",
    "num_picks",
    "num_p_picks",
    "num_s_picks",
}
LON_RANGE = (-155.35, -155.22)
LAT_RANGE = (19.37, 19.47)
TIME_TOLERANCE_SEC = 1.5
MEAN_HORIZONTAL_ERROR_KM = 4.0
MAX_HORIZONTAL_ERROR_KM = 7.5
MAX_DEPTH_ERROR_KM = 2.0


def load_features(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text())
    assert payload.get("type") == "FeatureCollection", "Output must be a GeoJSON FeatureCollection"
    features = payload.get("features")
    assert isinstance(features, list) and features, "GeoJSON must contain at least one feature"

    rows = []
    for index, feature in enumerate(features):
        assert feature.get("type") == "Feature", f"Feature {index} must have type=Feature"
        geometry = feature.get("geometry") or {}
        assert geometry.get("type") == "Point", f"Feature {index} must use Point geometry"
        coordinates = geometry.get("coordinates")
        assert isinstance(coordinates, list) and len(coordinates) == 2, (
            f"Feature {index} must provide [longitude, latitude] coordinates"
        )

        properties = feature.get("properties") or {}
        missing = REQUIRED_PROPERTIES - set(properties)
        assert not missing, f"Feature {index} is missing properties: {sorted(missing)}"

        rows.append(
            {
                "time": properties["time"],
                "longitude": float(coordinates[0]),
                "latitude": float(coordinates[1]),
                "depth_km": float(properties["depth_km"]),
                "num_picks": int(properties["num_picks"]),
                "num_p_picks": int(properties["num_p_picks"]),
                "num_s_picks": int(properties["num_s_picks"]),
            }
        )

    catalog = pd.DataFrame(rows)
    catalog["time"] = pd.to_datetime(catalog["time"])
    return catalog.sort_values("time").reset_index(drop=True)


def load_expected(path: Path) -> pd.DataFrame:
    catalog = pd.read_csv(path)
    catalog["time"] = pd.to_datetime(catalog["time"])
    return catalog.sort_values("time").reset_index(drop=True)


def horizontal_error_km(predicted: pd.Series, expected: pd.Series) -> float:
    mean_lat = math.radians((predicted["latitude"] + expected["latitude"]) / 2.0)
    dx = (predicted["longitude"] - expected["longitude"]) * 111.32 * math.cos(mean_lat)
    dy = (predicted["latitude"] - expected["latitude"]) * 111.32
    return math.hypot(dx, dy)


def match_events(predicted: pd.DataFrame, expected: pd.DataFrame):
    matches = []
    used = set()
    for expected_index, expected_row in expected.iterrows():
        best_index = None
        best_dt = None
        for predicted_index, predicted_row in predicted.iterrows():
            if predicted_index in used:
                continue
            dt = abs((predicted_row["time"] - expected_row["time"]).total_seconds())
            if dt > TIME_TOLERANCE_SEC:
                continue
            if best_dt is None or dt < best_dt:
                best_dt = dt
                best_index = predicted_index
        assert best_index is not None, f"Expected event at {expected_row['time']} was not recovered"
        used.add(best_index)
        matches.append((predicted.loc[best_index], expected_row))
    return matches


def test_geojson_schema_and_monitoring_bounds():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    catalog = load_features(OUTPUT_PATH)
    expected = load_expected(EXPECTED_PATH)

    assert len(catalog) == len(expected), f"Expected {len(expected)} swarm events, found {len(catalog)}"
    assert catalog["time"].is_unique, "Each feature should represent a unique event"
    assert catalog["longitude"].between(*LON_RANGE).all()
    assert catalog["latitude"].between(*LAT_RANGE).all()
    assert (catalog["depth_km"] >= 0.0).all()
    assert (catalog["num_picks"] == catalog["num_p_picks"] + catalog["num_s_picks"]).all()
    assert (catalog["num_picks"] >= 12).all()
    assert (catalog["num_p_picks"] >= 6).all()
    assert (catalog["num_s_picks"] >= 6).all()


def test_geojson_features_match_expected_swarm():
    catalog = load_features(OUTPUT_PATH)
    expected = load_expected(EXPECTED_PATH)
    matches = match_events(catalog, expected)

    horizontal_errors = [
        horizontal_error_km(predicted, expected_row)
        for predicted, expected_row in matches
    ]
    depth_errors = [
        abs(predicted["depth_km"] - expected_row["depth_km"])
        for predicted, expected_row in matches
    ]

    assert pd.Series(horizontal_errors).mean() <= MEAN_HORIZONTAL_ERROR_KM
    assert max(horizontal_errors) <= MAX_HORIZONTAL_ERROR_KM
    assert max(depth_errors) <= MAX_DEPTH_ERROR_KM
