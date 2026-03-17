import json
import os

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ROUTES_FILE = os.environ.get(
    "ROUTES_FILE",
    "/root/ferry_routes.geojson"
    if os.path.exists("/root/ferry_routes.geojson")
    else os.path.join(BASE_DIR, "environment", "ferry_routes.geojson"),
)
ZONES_FILE = os.environ.get(
    "ZONES_FILE",
    "/root/seasonal_slow_zones.geojson"
    if os.path.exists("/root/seasonal_slow_zones.geojson")
    else os.path.join(BASE_DIR, "environment", "seasonal_slow_zones.geojson"),
)
OUTPUT_CANDIDATES = ["/root/ferry_slowzone_overlap.json", "ferry_slowzone_overlap.json"]
TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True)


def load_geojson(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_result():
    for candidate in OUTPUT_CANDIDATES:
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as handle:
                return json.load(handle)
    raise FileNotFoundError("Missing /root/ferry_slowzone_overlap.json")


def project_geometry(geom):
    return transform(TRANSFORMER.transform, geom)


def load_route_features():
    return load_geojson(ROUTES_FILE)["features"]


def load_zone_features():
    return load_geojson(ZONES_FILE)["features"]


def compute_expected():
    route_features = load_route_features()
    spring_zone_features = [
        feature
        for feature in load_zone_features()
        if feature["properties"]["season"] == "spring"
    ]
    spring_union = unary_union([shape(feature["geometry"]) for feature in spring_zone_features])

    best = None

    for feature in route_features:
        geom = shape(feature["geometry"])
        overlap_length_km = project_geometry(geom.intersection(spring_union)).length / 1000.0
        zone_ids = sorted(
            {
                zone_feature["properties"]["zone_id"]
                for zone_feature in spring_zone_features
                if geom.intersects(shape(zone_feature["geometry"]))
            }
        )
        candidate = {
            "season": "spring",
            "route_id": feature["properties"]["route_id"],
            "route_name": feature["properties"]["route_name"],
            "operator": feature["properties"]["operator"],
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
        raise AssertionError("No route features found.")

    return best[1]


def compute_all_season_winner():
    route_features = load_route_features()
    all_zone_features = load_zone_features()
    all_union = unary_union([shape(feature["geometry"]) for feature in all_zone_features])

    best = None
    for feature in route_features:
        geom = shape(feature["geometry"])
        overlap_length_km = project_geometry(geom.intersection(all_union)).length / 1000.0
        route_id = feature["properties"]["route_id"]
        if best is None or overlap_length_km > best[0] + 1e-9 or (
            abs(overlap_length_km - best[0]) <= 1e-9 and route_id < best[1]
        ):
            best = (overlap_length_km, route_id)

    return best[1]


def test_output_structure():
    result = load_result()
    assert set(result.keys()) == {
        "season",
        "route_id",
        "route_name",
        "operator",
        "intersecting_zone_ids",
        "overlap_length_km",
    }


def test_matches_recomputed_winner():
    result = load_result()
    expected = compute_expected()
    assert result["season"] == expected["season"]
    assert result["route_id"] == expected["route_id"]
    assert result["route_name"] == expected["route_name"]
    assert result["operator"] == expected["operator"]
    assert result["intersecting_zone_ids"] == expected["intersecting_zone_ids"]
    assert abs(result["overlap_length_km"] - expected["overlap_length_km"]) <= 0.01


def test_intersecting_zone_ids_are_sorted_unique_spring_ids():
    result = load_result()
    expected = compute_expected()
    assert result["season"] == "spring"
    assert result["intersecting_zone_ids"] == sorted(set(result["intersecting_zone_ids"]))
    assert result["intersecting_zone_ids"] == expected["intersecting_zone_ids"]


def test_reported_overlap_is_positive_and_rounded():
    result = load_result()
    assert isinstance(result["overlap_length_km"], (int, float))
    assert result["overlap_length_km"] > 0.0
    assert abs(result["overlap_length_km"] - round(result["overlap_length_km"], 2)) <= 1e-9


def test_fixture_requires_spring_filter():
    assert compute_expected()["route_id"] != compute_all_season_winner()
