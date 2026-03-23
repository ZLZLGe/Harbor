import csv
import json
from pathlib import Path


OUTPUT = Path("/root/transfer2_claim_audit.json")
REQUEST = Path("/root/data/transfer2_claims.json")
DATA = Path("/root/data/restaurants/clean_restaurant_2022.csv")


def load_rows():
    with DATA.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_expected_reviews():
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    rows = load_rows()
    reviews = []
    for claim in request["claims"]:
        city_rows = [row for row in rows if row["City"].strip() == claim["city"]]
        match = next((row for row in city_rows if row["Name"].strip() == claim["restaurant_name"].strip()), None)
        if match is None:
            reviews.append(
                {
                    "claim_id": claim["claim_id"],
                    "status": "rejected",
                    "reasons": ["not_found"],
                    "matched_restaurant": None,
                    "average_cost": None,
                    "aggregate_rating": None,
                }
            )
            continue

        reasons = []
        if claim["required_cuisine"].lower() not in match["Cuisines"].lower():
            reasons.append("cuisine_mismatch")
        if float(match["Average Cost"]) > float(claim["max_average_cost"]):
            reasons.append("cost_exceeded")
        if float(match["Aggregate Rating"]) < float(claim["min_aggregate_rating"]):
            reasons.append("rating_below_min")

        reviews.append(
            {
                "claim_id": claim["claim_id"],
                "status": "approved" if not reasons else "rejected",
                "reasons": reasons,
                "matched_restaurant": match["Name"],
                "average_cost": float(match["Average Cost"]),
                "aggregate_rating": float(match["Aggregate Rating"]),
            }
        )
    return request, reviews


def test_output_exists():
    assert OUTPUT.exists(), "missing claim audit output"


def test_payload_matches_expected_audit():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    request, reviews = build_expected_reviews()

    assert payload["batch_name"] == request["batch_name"]
    assert payload["claim_reviews"] == reviews
    assert payload["approved_claim_ids"] == [item["claim_id"] for item in reviews if item["status"] == "approved"]
    assert payload["tool_called"] == ["search_restaurants"]


def test_known_approval_and_rejection_mix():
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    review_map = {item["claim_id"]: item for item in payload["claim_reviews"]}

    assert payload["approved_claim_ids"] == ["CLM-001", "CLM-004", "CLM-005"]
    assert review_map["CLM-002"]["reasons"] == ["cost_exceeded"]
    assert review_map["CLM-003"]["reasons"] == ["cuisine_mismatch"]
    assert review_map["CLM-006"]["reasons"] == ["rating_below_min"]
    assert review_map["CLM-007"]["reasons"] == ["not_found"]
