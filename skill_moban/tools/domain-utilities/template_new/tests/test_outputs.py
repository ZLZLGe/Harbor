from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conftest import OUTPUT_PATH, load_output_json
from reference_scoring import build_expected_report


def _index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["domain"]: row for row in rows}


def test_a_output_exists_and_parses() -> None:
    assert OUTPUT_PATH.exists(), OUTPUT_PATH
    assert OUTPUT_PATH.stat().st_size > 0
    payload = load_output_json()
    assert payload["segment"] == "field-service-dispatch-intelligence"
    assert isinstance(payload["buy_now_ranked"], list)
    assert isinstance(payload["evaluations"], list)


def test_b_all_candidates_are_covered_once() -> None:
    payload = load_output_json()
    expected = build_expected_report()
    assert [row["domain"] for row in payload["evaluations"]] == sorted(
        row["domain"] for row in expected["evaluations"]
    )


def test_c_scores_and_statuses_match_policy_recomputation() -> None:
    payload = load_output_json()
    expected = build_expected_report()
    actual_index = _index(payload["evaluations"])
    expected_index = _index(expected["evaluations"])
    for domain, expected_row in expected_index.items():
        actual = actual_index[domain]
        for field in [
            "status",
            "market_fit_score",
            "authority_score",
            "commercial_intent_score",
            "legal_risk_score",
            "price_ceiling_usd",
            "total_score",
        ]:
            assert actual[field] == expected_row[field], (domain, field, actual[field], expected_row[field])


def test_d_ranked_shortlist_matches_true_best_candidates() -> None:
    payload = load_output_json()
    expected = build_expected_report()
    assert len(payload["buy_now_ranked"]) == 3
    assert payload["buy_now_ranked"] == expected["buy_now_ranked"]
    assert payload["top_pick"] == expected["top_pick"]


def test_e_reason_codes_and_evidence_are_grounded() -> None:
    payload = load_output_json()
    expected = build_expected_report()
    actual_index = _index(payload["evaluations"])
    expected_index = _index(expected["evaluations"])
    for domain, expected_row in expected_index.items():
        actual = actual_index[domain]
        actual_codes = set(actual["reason_codes"])
        for code in expected_row["reason_codes"]:
            assert code in actual_codes, (domain, code)
        assert len(actual["evidence"]) >= 2
        evidence_pairs = {(row["source"], row["key"], str(row["value"])) for row in actual["evidence"]}
        required_pairs = {
            (row["source"], row["key"], str(row["value"])) for row in expected_row["evidence"][:3]
        }
        assert required_pairs.issubset(evidence_pairs), (domain, evidence_pairs)
