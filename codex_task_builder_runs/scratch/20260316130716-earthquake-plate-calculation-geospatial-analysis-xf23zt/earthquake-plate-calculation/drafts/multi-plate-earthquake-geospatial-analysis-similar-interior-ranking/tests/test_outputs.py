import json
import os


EXPECTED_TOP_LEVEL = {
    "winning_plate": {
        "plate_code": "PA",
        "plate_name": "Pacific",
    },
    "winning_earthquake": {
        "id": "hv74103036",
        "place": "2 km SW of Pāhala, Hawaii",
        "time": "2024-02-09T20:06:31Z",
        "magnitude": 5.88,
        "latitude": 19.1868333333333,
        "longitude": -155.493166666667,
    },
    "winning_distance_km": 3878.27,
}

EXPECTED_RANKINGS = [
    {
        "plate_code": "PA",
        "plate_name": "Pacific",
        "earthquake_count_inside": 107,
        "id": "hv74103036",
        "place": "2 km SW of Pāhala, Hawaii",
        "time": "2024-02-09T20:06:31Z",
        "magnitude": 5.88,
        "latitude": 19.1868333333333,
        "longitude": -155.493166666667,
        "distance_km": 3878.27,
    },
    {
        "plate_code": "NZ",
        "plate_name": "Nazca",
        "earthquake_count_inside": 27,
        "id": "us6000m4af",
        "place": "southeast central Pacific Ocean",
        "time": "2024-01-17T21:34:10Z",
        "magnitude": 5.0,
        "latitude": -28.9612,
        "longitude": -93.9187,
        "distance_km": 895.25,
    },
    {
        "plate_code": "PS",
        "plate_name": "Philippine Sea",
        "earthquake_count_inside": 114,
        "id": "us7000mxmu",
        "place": "Bonin Islands, Japan region",
        "time": "2024-07-07T20:01:12Z",
        "magnitude": 6.2,
        "latitude": 26.8957,
        "longitude": 138.8289,
        "distance_km": 492.24,
    },
    {
        "plate_code": "CO",
        "plate_name": "Cocos",
        "earthquake_count_inside": 3,
        "id": "us6000mzmh",
        "place": "148 km SW of La Placita de Morelos, Mexico",
        "time": "2024-05-19T09:39:41Z",
        "magnitude": 5.2,
        "latitude": 17.58,
        "longitude": -104.5705,
        "distance_km": 72.24,
    },
]

FLOAT_TOLERANCE = 0.01
COORD_TOLERANCE = 0.0001


def load_result():
    for candidate in ("/root/plate_interior_winner.json", "plate_interior_winner.json"):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as handle:
                return json.load(handle)
    raise FileNotFoundError("Missing /root/plate_interior_winner.json")


def assert_close(actual, expected, tolerance):
    assert isinstance(actual, (int, float)), f"Expected numeric value, got {type(actual)!r}"
    assert abs(actual - expected) <= tolerance, (
        f"Expected {expected} ± {tolerance}, got {actual}"
    )


def test_top_level_structure():
    result = load_result()
    assert set(result.keys()) == {
        "winning_plate",
        "winning_earthquake",
        "winning_distance_km",
        "plate_rankings",
    }


def test_winning_plate_and_earthquake():
    result = load_result()
    assert result["winning_plate"] == EXPECTED_TOP_LEVEL["winning_plate"]

    winning_eq = result["winning_earthquake"]
    expected_eq = EXPECTED_TOP_LEVEL["winning_earthquake"]
    assert winning_eq["id"] == expected_eq["id"]
    assert winning_eq["place"] == expected_eq["place"]
    assert winning_eq["time"] == expected_eq["time"]
    assert_close(winning_eq["magnitude"], expected_eq["magnitude"], FLOAT_TOLERANCE)
    assert_close(winning_eq["latitude"], expected_eq["latitude"], COORD_TOLERANCE)
    assert_close(winning_eq["longitude"], expected_eq["longitude"], COORD_TOLERANCE)
    assert_close(
        result["winning_distance_km"],
        EXPECTED_TOP_LEVEL["winning_distance_km"],
        FLOAT_TOLERANCE,
    )


def test_plate_rankings_exact_order():
    result = load_result()
    rankings = result["plate_rankings"]
    assert isinstance(rankings, list)
    assert len(rankings) == 4

    for actual, expected in zip(rankings, EXPECTED_RANKINGS):
        assert actual["plate_code"] == expected["plate_code"]
        assert actual["plate_name"] == expected["plate_name"]
        assert actual["earthquake_count_inside"] == expected["earthquake_count_inside"]
        assert actual["id"] == expected["id"]
        assert actual["place"] == expected["place"]
        assert actual["time"] == expected["time"]
        assert_close(actual["magnitude"], expected["magnitude"], FLOAT_TOLERANCE)
        assert_close(actual["latitude"], expected["latitude"], COORD_TOLERANCE)
        assert_close(actual["longitude"], expected["longitude"], COORD_TOLERANCE)
        assert_close(actual["distance_km"], expected["distance_km"], FLOAT_TOLERANCE)


def test_plate_rankings_descending():
    result = load_result()
    distances = [row["distance_km"] for row in result["plate_rankings"]]
    assert distances == sorted(distances, reverse=True)


def test_top_level_matches_first_ranking():
    result = load_result()
    first = result["plate_rankings"][0]
    assert result["winning_plate"]["plate_code"] == first["plate_code"]
    assert result["winning_plate"]["plate_name"] == first["plate_name"]
    assert result["winning_earthquake"]["id"] == first["id"]
    assert result["winning_earthquake"]["place"] == first["place"]
    assert result["winning_earthquake"]["time"] == first["time"]
    assert_close(
        result["winning_earthquake"]["magnitude"],
        first["magnitude"],
        FLOAT_TOLERANCE,
    )
    assert_close(
        result["winning_earthquake"]["latitude"],
        first["latitude"],
        COORD_TOLERANCE,
    )
    assert_close(
        result["winning_earthquake"]["longitude"],
        first["longitude"],
        COORD_TOLERANCE,
    )
    assert_close(result["winning_distance_km"], first["distance_km"], FLOAT_TOLERANCE)
