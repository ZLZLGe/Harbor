from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd

from reference_metrics import build_bundle, latest_common_price_date, read_universe, risk_free_rate


OUTPUT_ROOT = Path(os.environ.get("FINANCE_OUTPUT_ROOT", "/app/output"))

FINANCIAL_PATH = OUTPUT_ROOT / "financial_metrics.csv"
SCORES_PATH = OUTPUT_ROOT / "quality_risk_scores.csv"
VALUATION_PATH = OUTPUT_ROOT / "valuation.json"
RANKING_PATH = OUTPUT_ROOT / "investment_ranking.json"
MEMO_PATH = OUTPUT_ROOT / "research_memo.md"


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value: Any) -> float:
    return float(value)


def assert_close(actual: Any, expected: Any, tol: float = 1e-4) -> None:
    assert math.isfinite(float(actual)), actual
    assert abs(float(actual) - float(expected)) <= tol, (actual, expected)


def assert_row_close(actual: dict[str, Any], expected: dict[str, Any], tol: float = 1e-4) -> None:
    for key, expected_value in expected.items():
        assert key in actual
        if isinstance(expected_value, (int, float)) and not isinstance(expected_value, bool):
            assert_close(actual[key], expected_value, tol)
        else:
            assert actual[key] == expected_value


def round_expected(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: round_expected(item) for key, item in value.items()}
    if isinstance(value, list):
        return [round_expected(item) for item in value]
    return value


def test_a_required_outputs_exist_and_parse() -> None:
    for path in [FINANCIAL_PATH, SCORES_PATH, VALUATION_PATH, RANKING_PATH, MEMO_PATH]:
        assert path.exists(), path
        assert path.stat().st_size > 0, path

    assert len(read_csv_rows(FINANCIAL_PATH)) == len(read_universe()) * 3
    assert len(read_csv_rows(SCORES_PATH)) == len(read_universe())
    assert isinstance(load_json(VALUATION_PATH), dict)
    assert isinstance(load_json(RANKING_PATH), dict)
    assert MEMO_PATH.read_text(encoding="utf-8").startswith("# ")


def test_b_financial_metrics_match_sec_recomputation() -> None:
    bundle = build_bundle()
    expected = sorted(bundle["financial_metrics"], key=lambda row: (row["ticker"], int(row["fiscal_year"])))
    actual = sorted(read_csv_rows(FINANCIAL_PATH), key=lambda row: (row["ticker"], int(row["fiscal_year"])))

    expected_columns = [
        "ticker",
        "company",
        "fiscal_year",
        "revenue",
        "operating_income",
        "net_income",
        "operating_cash_flow",
        "capital_expenditures",
        "free_cash_flow",
        "cash_and_equivalents",
        "total_debt",
        "stockholders_equity",
        "diluted_shares",
        "diluted_eps",
    ]
    assert list(actual[0].keys()) == expected_columns
    assert len(actual) == len(expected)
    for actual_row, expected_row in zip(actual, expected, strict=True):
        for field in ["ticker", "company"]:
            assert actual_row[field] == expected_row[field]
        assert int(actual_row["fiscal_year"]) == int(expected_row["fiscal_year"])
        for field in expected_columns[3:]:
            assert_close(actual_row[field], expected_row[field], tol=1e-2)
        assert_close(
            float(actual_row["free_cash_flow"]),
            float(actual_row["operating_cash_flow"]) - float(actual_row["capital_expenditures"]),
            tol=1e-4,
        )


def test_c_quality_risk_scores_match_recomputation_and_rank_order() -> None:
    bundle = build_bundle()
    expected = sorted(bundle["quality_risk_scores"], key=lambda row: row["ticker"])
    actual = sorted(read_csv_rows(SCORES_PATH), key=lambda row: row["ticker"])

    expected_columns = [
        "ticker",
        "revenue_cagr_3y",
        "operating_margin_latest",
        "net_margin_latest",
        "fcf_margin_latest",
        "return_on_equity_latest",
        "net_cash_to_revenue_latest",
        "eps_growth_3y",
        "total_return_252d",
        "annualized_volatility",
        "max_drawdown",
        "beta_to_spy",
        "sharpe_ratio",
        "composite_score",
        "rank",
    ]
    assert list(actual[0].keys()) == expected_columns
    assert [row["ticker"] for row in actual] == [row["ticker"] for row in expected]
    for actual_row, expected_row in zip(actual, expected, strict=True):
        assert actual_row["ticker"] == expected_row["ticker"]
        assert int(actual_row["rank"]) == int(expected_row["rank"])
        for field in expected_columns[1:-1]:
            assert_close(actual_row[field], expected_row[field], tol=1e-4)

    ranked = sorted(read_csv_rows(SCORES_PATH), key=lambda row: int(row["rank"]))
    composite_scores = [as_float(row["composite_score"]) for row in ranked]
    assert composite_scores == sorted(composite_scores, reverse=True)
    assert [int(row["rank"]) for row in ranked] == list(range(1, len(ranked) + 1))


def test_d_valuation_json_matches_recomputation() -> None:
    expected = round_expected(build_bundle()["valuation"])
    actual = load_json(VALUATION_PATH)

    assert actual["as_of_date"] == expected["as_of_date"]
    assert_close(actual["risk_free_rate"], expected["risk_free_rate"], tol=1e-6)
    assert [item["ticker"] for item in actual["securities"]] == [item["ticker"] for item in expected["securities"]]
    for actual_item, expected_item in zip(actual["securities"], expected["securities"], strict=True):
        assert actual_item["ticker"] == expected_item["ticker"]
        assert actual_item["recommendation"] == expected_item["recommendation"]
        for field in [
            "latest_price",
            "base_fair_value",
            "bull_fair_value",
            "bear_fair_value",
            "base_upside_pct",
            "margin_of_safety",
        ]:
            assert_close(actual_item[field], expected_item[field], tol=1e-4)


def test_e_investment_ranking_matches_scores_and_recommendations() -> None:
    expected = round_expected(build_bundle()["investment_ranking"])
    actual = load_json(RANKING_PATH)

    assert actual["top_pick"] == expected["top_pick"]
    assert actual["avoid_or_trim"] == expected["avoid_or_trim"]
    assert [row["ticker"] for row in actual["ranking"]] == [row["ticker"] for row in expected["ranking"]]
    for actual_row, expected_row in zip(actual["ranking"], expected["ranking"], strict=True):
        assert actual_row["rank"] == expected_row["rank"]
        assert actual_row["ticker"] == expected_row["ticker"]
        assert actual_row["recommendation"] == expected_row["recommendation"]
        assert_close(actual_row["composite_score"], expected_row["composite_score"], tol=1e-4)
        assert actual_row["primary_reason"]

    assert actual["top_pick"] == actual["ranking"][0]["ticker"]


def test_f_research_memo_is_consistent_with_structured_outputs() -> None:
    memo = MEMO_PATH.read_text(encoding="utf-8")
    scores = {row["ticker"]: row for row in read_csv_rows(SCORES_PATH)}
    valuation = {item["ticker"]: item for item in load_json(VALUATION_PATH)["securities"]}
    ranking = load_json(RANKING_PATH)["ranking"]

    for section in [
        "## Data Sources",
        "## Financial Quality",
        "## Market Risk",
        "## Valuation",
        "## Ranking And Recommendations",
    ]:
        assert section in memo

    top3 = [item["ticker"] for item in ranking[:3]]
    assert f"Top 3 tickers: {', '.join(top3)}" in memo
    for item in ranking:
        ticker = item["ticker"]
        assert f"Rank {item['rank']}: {ticker}" in memo
        assert item["recommendation"] in memo
        assert str(round(float(scores[ticker]["composite_score"]), 6)) in memo
        assert str(round(float(valuation[ticker]["base_upside_pct"]), 6)) in memo


def test_g_as_of_date_and_risk_free_rate_use_frozen_public_data() -> None:
    tickers = [row["ticker"] for row in read_universe()]
    as_of_date = latest_common_price_date(tickers)
    expected_rf = risk_free_rate(as_of_date)
    valuation = load_json(VALUATION_PATH)

    assert valuation["as_of_date"] == as_of_date.date().isoformat()
    assert_close(valuation["risk_free_rate"], expected_rf, tol=1e-6)

    fred = pd.read_csv(Path(os.environ.get("FINANCE_DATA_ROOT", "/app/data")) / "fred" / "DGS10.csv")
    assert valuation["risk_free_rate"] > 0
    assert fred["observation_date"].max() >= valuation["as_of_date"]
