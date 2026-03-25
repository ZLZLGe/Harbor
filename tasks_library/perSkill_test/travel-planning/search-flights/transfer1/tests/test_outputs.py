import csv
from pathlib import Path

import pandas as pd


OUTPUT = Path("/root/transfer1_manifest.csv")
REQUEST = Path("/root/data/transfer1_manifest_requests.csv")
FLIGHTS = Path("/root/data/flights/clean_Flights_2022.csv")


def choose_cheapest(df: pd.DataFrame):
    if df.empty:
        return None
    ordered = df.sort_values(["Price", "DepTime", "Flight Number"]).reset_index(drop=True)
    row = ordered.iloc[0]
    return {
        "selected_flight_number": row["Flight Number"],
        "selected_price": str(int(row["Price"])),
        "selected_departure": row["DepTime"],
        "selected_arrival": row["ArrTime"],
    }


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expected_rows():
    requests = read_csv(REQUEST)
    flights = pd.read_csv(FLIGHTS).rename(columns={"Unnamed: 0": "Flight Number"})
    expected = []
    for row in requests:
        subset = flights[
            (flights["OriginCityName"] == row["origin"])
            & (flights["DestCityName"] == row["destination"])
            & (flights["FlightDate"] == row["flight_date"])
        ]
        chosen = choose_cheapest(subset)
        expected.append(
            {
                "request_id": row["request_id"],
                "priority": row["priority"],
                "status": "AVAILABLE" if chosen else "NO_SERVICE",
                "origin": row["origin"],
                "destination": row["destination"],
                "flight_date": row["flight_date"],
                "selected_flight_number": "" if not chosen else chosen["selected_flight_number"],
                "selected_price": "" if not chosen else chosen["selected_price"],
                "selected_departure": "" if not chosen else chosen["selected_departure"],
                "selected_arrival": "" if not chosen else chosen["selected_arrival"],
                "tool_called": "search_flights",
            }
        )
    return expected


def test_output_exists():
    assert OUTPUT.exists(), "missing transfer1 output"


def test_csv_contract_and_values():
    actual = read_csv(OUTPUT)
    assert actual == expected_rows()


def test_known_available_and_no_service_rows():
    actual = read_csv(OUTPUT)
    rows = {row["request_id"]: row for row in actual}

    assert rows["A1"]["status"] == "AVAILABLE"
    assert rows["A1"]["selected_flight_number"] == "F3916848"
    assert rows["A1"]["selected_price"] == "147"

    assert rows["A5"]["selected_flight_number"] == "F0653729"
    assert rows["A5"]["selected_price"] == "57"

    assert rows["A4"]["status"] == "NO_SERVICE"
    assert rows["A4"]["selected_flight_number"] == ""
    assert rows["A6"]["status"] == "NO_SERVICE"
