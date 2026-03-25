import json
from datetime import datetime
from pathlib import Path

import pandas as pd


OUTPUT = Path("/root/transfer3_connection_screen.json")
REQUEST = Path("/root/data/transfer3_connection_candidates.json")
FLIGHTS = Path("/root/data/flights/clean_Flights_2022.csv")


def to_minutes(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def feasible_pairs(first_leg_df, second_leg_df, min_layover: int, max_layover: int):
    if first_leg_df.empty or second_leg_df.empty:
        return []
    pairs = []
    for _, first in first_leg_df.iterrows():
        first_arrival = to_minutes(first["ArrTime"])
        for _, second in second_leg_df.iterrows():
            layover = to_minutes(second["DepTime"]) - first_arrival
            if min_layover <= layover <= max_layover:
                pairs.append(
                    {
                        "first_leg_flight_number": first["Flight Number"],
                        "second_leg_flight_number": second["Flight Number"],
                        "first_leg_departure": first["DepTime"],
                        "first_leg_arrival": first["ArrTime"],
                        "second_leg_departure": second["DepTime"],
                        "second_leg_arrival": second["ArrTime"],
                        "layover_minutes": int(layover),
                        "total_price": int(first["Price"] + second["Price"]),
                    }
                )
    pairs.sort(
        key=lambda pair: (
            pair["total_price"],
            pair["layover_minutes"],
            pair["first_leg_departure"],
            pair["first_leg_flight_number"],
            pair["second_leg_flight_number"],
        )
    )
    return pairs


def expected_payload():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    flights = pd.read_csv(FLIGHTS).rename(columns={"Unnamed: 0": "Flight Number"})
    summaries = []
    for candidate in request["candidates"]:
        first_leg = candidate["first_leg"]
        second_leg = candidate["second_leg"]
        first_df = flights[
            (flights["OriginCityName"] == first_leg["origin"])
            & (flights["DestCityName"] == first_leg["destination"])
            & (flights["FlightDate"] == candidate["travel_date"])
        ]
        second_df = flights[
            (flights["OriginCityName"] == second_leg["origin"])
            & (flights["DestCityName"] == second_leg["destination"])
            & (flights["FlightDate"] == candidate["travel_date"])
        ]
        pairs = feasible_pairs(
            first_df,
            second_df,
            request["minimum_layover_minutes"],
            request["maximum_layover_minutes"],
        )
        summaries.append(
            {
                "connection_id": candidate["connection_id"],
                "travel_date": candidate["travel_date"],
                "first_leg_route": f"{first_leg['origin']} -> {first_leg['destination']}",
                "second_leg_route": f"{second_leg['origin']} -> {second_leg['destination']}",
                "status": "FEASIBLE" if pairs else "NO_FEASIBLE_CONNECTION",
                "feasible_connection_count": len(pairs),
                "best_connection": pairs[0] if pairs else None,
            }
        )

    eligible = [summary for summary in summaries if summary["best_connection"] is not None]
    eligible.sort(
        key=lambda summary: (
            summary["best_connection"]["total_price"],
            summary["best_connection"]["layover_minutes"],
            summary["connection_id"],
        )
    )
    selected = None
    if eligible:
        selected = {"connection_id": eligible[0]["connection_id"], **eligible[0]["best_connection"]}

    return {
        "analysis_id": request["analysis_id"],
        "minimum_layover_minutes": request["minimum_layover_minutes"],
        "maximum_layover_minutes": request["maximum_layover_minutes"],
        "candidate_summaries": summaries,
        "selected_connection": selected,
        "tool_called": ["search_flights"],
    }


def test_output_exists():
    assert OUTPUT.exists(), "missing transfer3 output"


def test_json_matches_expected_payload():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert payload == expected_payload()


def test_known_connection_winner_and_gap_case():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert payload["selected_connection"]["connection_id"] == "CX1"
    assert payload["selected_connection"]["first_leg_flight_number"] == "F0264647"
    assert payload["selected_connection"]["second_leg_flight_number"] == "F0181769"
    assert payload["selected_connection"]["layover_minutes"] == 112
    assert payload["selected_connection"]["total_price"] == 227

    summaries = {item["connection_id"]: item for item in payload["candidate_summaries"]}
    assert summaries["CX2"]["feasible_connection_count"] == 1
    assert summaries["CX4"]["status"] == "NO_FEASIBLE_CONNECTION"
    assert summaries["CX4"]["best_connection"] is None
