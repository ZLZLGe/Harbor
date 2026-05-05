from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, "/tests")
import reference_metrics


OUTPUT = Path("/root/answer")

PERFORMANCE_COLUMNS = [
    "store_id",
    "promo_id",
    "category_id",
    "business_start_date",
    "business_end_date",
    "net_revenue",
    "net_units",
    "gross_margin",
    "baseline_net_revenue",
    "promo_uplift_pct",
    "incremental_margin",
    "stockout_exposure_hours",
    "adjusted_roi",
    "reportable",
]

CATEGORY_COLUMNS = [
    "category_id",
    "category_name",
    "baseline_uplift_pct",
    "adjusted_uplift_pct",
    "adjusted_pvalue",
    "adjusted_qvalue",
    "direction",
    "diagnostic_status",
]

RISK_COLUMNS = [
    "store_id",
    "return_rate",
    "duplicate_rate",
    "stockout_exposure_hours",
    "weather_anomaly_days",
    "traffic_anomaly_days",
    "final_risk_level",
]


def expected_bundle() -> dict[str, pd.DataFrame]:
    inputs = reference_metrics.load_inputs()
    performance = reference_metrics.promo_performance(inputs)
    category = reference_metrics.category_uplift(performance, inputs["products"])
    risk = reference_metrics.store_risk_audit(inputs, performance)
    return {"performance": performance, "category": category, "risk": risk}


def read_outputs() -> dict[str, object]:
    return {
        "performance": pd.read_csv(OUTPUT / "promo_performance.csv"),
        "category": pd.read_csv(OUTPUT / "category_uplift.tsv", sep="\t"),
        "risk": pd.read_csv(OUTPUT / "store_risk_audit.tsv", sep="\t"),
        "diagnostics": pd.read_csv(OUTPUT / "analysis_diagnostics.tsv", sep="\t"),
        "roi_fig": pd.read_csv(OUTPUT / "figures" / "promo_roi_by_category.csv"),
        "risk_fig": pd.read_csv(OUTPUT / "figures" / "store_risk_matrix.csv"),
        "report": json.loads((OUTPUT / "promo_summary.json").read_text(encoding="utf-8")),
    }


def json_string_values(value: object) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        values: set[str] = {str(key) for key in value.keys()}
        for item in value.values():
            values.update(json_string_values(item))
        return values
    if isinstance(value, list):
        values: set[str] = set()
        for item in value:
            values.update(json_string_values(item))
        return values
    return set()


def test_required_outputs_exist_and_parse() -> None:
    required = [
        OUTPUT / "promo_performance.csv",
        OUTPUT / "category_uplift.tsv",
        OUTPUT / "store_risk_audit.tsv",
        OUTPUT / "analysis_diagnostics.tsv",
        OUTPUT / "promo_summary.json",
        OUTPUT / "figures" / "promo_roi_by_category.csv",
        OUTPUT / "figures" / "store_risk_matrix.csv",
    ]
    for path in required:
        assert path.exists(), path
    actual = read_outputs()
    assert set(PERFORMANCE_COLUMNS).issubset(actual["performance"].columns)
    assert set(CATEGORY_COLUMNS).issubset(actual["category"].columns)
    assert set(RISK_COLUMNS).issubset(actual["risk"].columns)
    assert set(actual["report"]) == {
        "analysis_window",
        "n_promotions",
        "n_store_promo_category_rows",
        "n_reportable_rows",
        "top_promotions",
        "category_summary",
        "risk_summary",
        "model_summary",
        "enrichment_summary",
        "notes",
    }


def test_promo_performance_matches_raw_event_reference() -> None:
    expected = expected_bundle()["performance"].copy()
    actual = read_outputs()["performance"].copy()
    expected = expected.sort_values(["promo_id", "store_id"]).reset_index(drop=True)
    actual = actual.sort_values(["promo_id", "store_id"]).reset_index(drop=True)
    identity_cols = ["store_id", "promo_id", "category_id", "business_start_date", "business_end_date"]
    assert_frame_equal(actual[identity_cols], expected[identity_cols], check_dtype=False)
    assert_frame_equal(
        actual[["net_revenue", "net_units", "gross_margin", "stockout_exposure_hours"]],
        expected[["net_revenue", "net_units", "gross_margin", "stockout_exposure_hours"]],
        check_dtype=False,
        atol=0.011,
        rtol=0.0001,
    )
    assert (actual["baseline_net_revenue"].astype(float) > 0).all()
    assert actual["promo_uplift_pct"].between(-100, 300).all()
    assert actual["adjusted_roi"].between(-10, 20).all()
    assert actual["stockout_exposure_hours"].sum() > 0
    assert actual["reportable"].any()
    assert (~actual["reportable"]).any()


def test_category_diagnostics_and_figures_are_consistent() -> None:
    bundle = expected_bundle()
    actual = read_outputs()
    actual_category = actual["category"][CATEGORY_COLUMNS].sort_values("category_id").reset_index(drop=True)
    expected_categories = set(bundle["category"]["category_id"])
    assert set(actual_category["category_id"]) == expected_categories
    assert actual_category["category_name"].notna().all()
    assert actual_category["adjusted_pvalue"].between(0, 1).all()
    assert actual_category["adjusted_qvalue"].between(0, 1).all()
    assert set(actual_category["direction"]).issubset({"up", "down"})
    assert actual_category["diagnostic_status"].nunique() >= 2

    diagnostics = actual["diagnostics"]
    expected_diagnostics = bundle["performance"].sort_values(["promo_id", "store_id"]).reset_index(drop=True)
    diagnostics = diagnostics.sort_values(["promo_id", "store_id"]).reset_index(drop=True)
    assert set(["diagnostic_status", "reportable", "stockout_exposure_hours"]).issubset(diagnostics.columns)
    assert diagnostics["diagnostic_status"].nunique() >= 3
    assert (diagnostics.loc[diagnostics["stockout_exposure_hours"] > 10, "reportable"].astype(str).str.lower() == "false").all()
    assert_frame_equal(
        diagnostics[["store_id", "promo_id", "category_id", "stockout_exposure_hours"]],
        expected_diagnostics[["store_id", "promo_id", "category_id", "stockout_exposure_hours"]],
        check_dtype=False,
        atol=0.011,
        rtol=0.0001,
    )
    if "net_revenue" in diagnostics.columns:
        assert_frame_equal(
            diagnostics[["store_id", "promo_id", "category_id", "net_revenue"]],
            expected_diagnostics[["store_id", "promo_id", "category_id", "net_revenue"]],
            check_dtype=False,
            atol=0.011,
            rtol=0.0001,
        )

    roi_fig = actual["roi_fig"]
    assert set(["category_id", "metric", "value"]).issubset(roi_fig.columns)
    assert set(roi_fig["category_id"]) == set(actual_category["category_id"])
    assert roi_fig["value"].notna().all()
    assert roi_fig["metric"].astype(str).str.contains("uplift|roi", case=False, regex=True).any()


def test_store_risk_and_risk_figure_are_consistent() -> None:
    bundle = expected_bundle()
    actual = read_outputs()
    actual_risk = actual["risk"][RISK_COLUMNS].sort_values("store_id").reset_index(drop=True)
    expected_risk = bundle["risk"][["store_id", "stockout_exposure_hours"]].sort_values("store_id").reset_index(drop=True)
    assert_frame_equal(
        actual_risk[["store_id", "stockout_exposure_hours"]],
        expected_risk,
        check_dtype=False,
        atol=0.011,
        rtol=0.0001,
    )
    assert actual_risk["return_rate"].between(0, 0.2).all()
    assert actual_risk["duplicate_rate"].between(0, 0.2).all()
    assert set(actual_risk["final_risk_level"]) >= {"medium", "high"}

    risk_fig = actual["risk_fig"]
    assert set(risk_fig["store_id"]) == set(actual_risk["store_id"])
    assert set(["return_rate", "duplicate_rate", "stockout_exposure_hours"]).issubset(
        set(risk_fig["risk_factor"])
    )


def test_report_uses_same_tables_and_real_enrichment_service() -> None:
    bundle = expected_bundle()
    actual = read_outputs()
    report = actual["report"]
    performance = actual["performance"]
    category = actual["category"]
    risk = actual["risk"]

    assert report["n_promotions"] == 3
    assert report["n_store_promo_category_rows"] == len(performance)
    assert report["n_reportable_rows"] == int(performance["reportable"].sum())
    expected_risk_counts = risk.groupby("final_risk_level").size().to_dict()
    if "risk_level_counts" in report["risk_summary"]:
        assert report["risk_summary"]["risk_level_counts"] == expected_risk_counts
    elif "counts_by_level" in report["risk_summary"]:
        assert report["risk_summary"]["counts_by_level"] == expected_risk_counts
    elif "counts_by_risk_level" in report["risk_summary"]:
        assert report["risk_summary"]["counts_by_risk_level"] == expected_risk_counts
    elif "by_level" in report["risk_summary"]:
        assert report["risk_summary"]["by_level"] == expected_risk_counts
    elif "by_risk_level" in report["risk_summary"]:
        assert report["risk_summary"]["by_risk_level"] == expected_risk_counts
    elif "final_risk_levels" in report["risk_summary"]:
        assert report["risk_summary"]["final_risk_levels"] == expected_risk_counts
    else:
        assert report["risk_summary"] == expected_risk_counts
    assert {row["category_id"] for row in report["category_summary"]} == set(category["category_id"])
    assert report["enrichment_summary"]["service"] == "promo-enrichment"
    enrichment_strings = json_string_values(report["enrichment_summary"])
    report_strings = json_string_values(report)
    assert set(performance["promo_id"]).issubset(enrichment_strings | report_strings)
    assert set(category["category_id"]).issubset(enrichment_strings | report_strings)
    assert set(performance["store_id"]).issubset(enrichment_strings | report_strings)
    assert "local_business_date" in report["model_summary"]["controlled_factors"]
    assert "stockout_exposure_hours" in report["model_summary"]["controlled_factors"]
    assert report["model_summary"]["baseline_formula"] != report["model_summary"]["adjusted_formula"]

    valid_keys = set(zip(performance["store_id"], performance["promo_id"], performance["category_id"]))
    for row in report["top_promotions"]:
        assert (row["store_id"], row["promo_id"], row["category_id"]) in valid_keys
    assert len(report["top_promotions"]) <= 5


def test_guardrail_not_naive_utc_duplicate_pipeline() -> None:
    actual = read_outputs()
    performance = actual["performance"]
    diagnostics = actual["diagnostics"]
    report = actual["report"]

    assert performance["stockout_exposure_hours"].sum() > 20
    assert diagnostics["diagnostic_status"].nunique() >= 3
    if "adjusted_baseline_net_revenue" in diagnostics.columns:
        assert diagnostics["adjusted_baseline_net_revenue"].notna().all()
    if "adjusted_uplift_pct" in diagnostics.columns:
        assert (diagnostics["promo_uplift_pct"].round(3) != diagnostics["adjusted_uplift_pct"].round(3)).any()
    assert "UTC naive" not in json.dumps(report)
    assert report["enrichment_summary"].get("service") != "not_called"
