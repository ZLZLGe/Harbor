import json
from pathlib import Path

import pandas as pd


OUTPUT = Path("/root/similar_roundtrip_brief.json")
REQUEST = Path("/root/data/similar_roundtrip_requests.json")
FLIGHTS = Path("/root/data/flights/clean_Flights_2022.csv")


def choose_cheapest(df: pd.DataFrame):
    if df.empty:
        return None
    ordered = df.sort_values(["Price", "DepTime", "Flight Number"]).reset_index(drop=True)
    row = ordered.iloc[0]
    return {
        "origin": row["OriginCityName"],
        "destination": row["DestCityName"],
        "flight_date": row["FlightDate"],
        "flight_number": row["Flight Number"],
        "price": int(row["Price"]),
        "departure_time": row["DepTime"],
        "arrival_time": row["ArrTime"],
    }


def evaluate_expected():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    flights = pd.read_csv(FLIGHTS).rename(columns={"Unnamed: 0": "Flight Number"})
    evaluated = []
    for candidate in request["candidates"]:
        outbound_req = candidate["outbound"]
        return_req = candidate["return"]
        outbound_df = flights[
            (flights["OriginCityName"] == outbound_req["origin"])
            & (flights["DestCityName"] == outbound_req["destination"])
            & (flights["FlightDate"] == outbound_req["flight_date"])
        ]
        return_df = flights[
            (flights["OriginCityName"] == return_req["origin"])
            & (flights["DestCityName"] == return_req["destination"])
            & (flights["FlightDate"] == return_req["flight_date"])
        ]
        outbound_pick = choose_cheapest(outbound_df)
        return_pick = choose_cheapest(return_df)
        available = outbound_pick is not None and return_pick is not None
        evaluated.append(
            {
                "option_id": candidate["option_id"],
                "route_label": candidate["route_label"],
                "available": available,
                "outbound": outbound_pick if available else None,
                "return": return_pick if available else None,
                "total_price": (
                    outbound_pick["price"] + return_pick["price"]
                    if available
                    else None
                ),
            }
        )

    eligible = [
        option
        for option in evaluated
        if option["available"] and option["total_price"] <= request["budget_cap"]
    ]
    eligible.sort(
        key=lambda option: (
            option["total_price"],
            option["outbound"]["departure_time"],
            option["option_id"],
        )
    )
    return request, evaluated, eligible[0] if eligible else None


def test_output_exists():
    assert OUTPUT.exists(), "missing similar output"


def test_payload_matches_expected_evaluation():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    request, expected_evaluated, expected_selected = evaluate_expected()

    assert payload["request_id"] == request["request_id"]
    assert payload["budget_cap"] == request["budget_cap"]
    assert payload["tool_called"] == ["search_flights"]
    assert payload["evaluated_options"] == expected_evaluated
    assert payload["selected_option"] == expected_selected


def test_known_winner_and_unavailable_case():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    selected = payload["selected_option"]
    assert selected["option_id"] == "northstar"
    assert selected["total_price"] == 87
    assert selected["outbound"]["flight_number"] == "F3325229"
    assert selected["return"]["flight_number"] == "F3189547"

    prairie = next(item for item in payload["evaluated_options"] if item["option_id"] == "prairie")
    assert prairie["available"] is False
    assert prairie["outbound"] is None
    assert prairie["return"] is None
    assert prairie["total_price"] is None
