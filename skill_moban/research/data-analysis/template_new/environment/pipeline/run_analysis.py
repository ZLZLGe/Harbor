#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DATA_ROOT = Path("/root/environment/data")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/root/answer")
    args = parser.parse_args()
    output = Path(args.output)
    (output / "figures").mkdir(parents=True, exist_ok=True)

    events = pd.read_csv(DATA_ROOT / "pos" / "transaction_events.csv")
    products = pd.read_csv(DATA_ROOT / "catalog" / "products.csv")
    promos = pd.read_csv(DATA_ROOT / "catalog" / "promotions.csv")
    stores = pd.read_csv(DATA_ROOT / "catalog" / "stores.csv")

    # Deliberately naive baseline: UTC dates, duplicate rows, no final-status
    # correction, no stockout exposure, no weather/holiday/traffic adjustment.
    events["business_date"] = pd.to_datetime(events["event_at_utc"], utc=True).dt.date.astype(str)
    events = events.merge(products[["product_id", "category_id", "category_name"]], on="product_id", how="left")
    events["net_revenue"] = events["unit_price"].astype(float) * events["quantity"].astype(int) - events[
        "discount_amount"
    ].astype(float)
    events["gross_margin"] = (
        (events["unit_price"].astype(float) - events["unit_cost"].astype(float)) * events["quantity"].astype(int)
        - events["discount_amount"].astype(float)
    )
    rows = []
    for promo in promos.to_dict("records"):
        start = pd.to_datetime(promo["business_start_date"]).date()
        end = pd.to_datetime(promo["business_end_date"]).date()
        base_start = start - pd.Timedelta(days=7)
        for store_id in stores["store_id"]:
            subset = events[(events["store_id"].eq(store_id)) & (events["category_id"].eq(promo["category_id"]))]
            dates = pd.to_datetime(subset["business_date"]).dt.date
            promo_rows = subset[(dates >= start) & (dates <= end)]
            base_rows = subset[(dates >= base_start) & (dates < start)]
            baseline = float(base_rows["net_revenue"].sum())
            revenue = float(promo_rows["net_revenue"].sum())
            uplift = 0.0 if baseline <= 0 else revenue / baseline - 1.0
            rows.append(
                {
                    "store_id": store_id,
                    "promo_id": promo["promo_id"],
                    "category_id": promo["category_id"],
                    "business_start_date": promo["business_start_date"],
                    "business_end_date": promo["business_end_date"],
                    "net_revenue": round(revenue, 2),
                    "net_units": int(promo_rows["quantity"].sum()),
                    "gross_margin": round(float(promo_rows["gross_margin"].sum()), 2),
                    "baseline_net_revenue": round(baseline, 2),
                    "promo_uplift_pct": round(uplift * 100, 3),
                    "incremental_margin": round(float(promo_rows["gross_margin"].sum() - base_rows["gross_margin"].sum()), 2),
                    "stockout_exposure_hours": 0.0,
                    "adjusted_roi": round(uplift, 4),
                    "reportable": uplift > 0.05,
                }
            )
    performance = pd.DataFrame(rows)
    performance.to_csv(output / "promo_performance.csv", index=False)
    category = (
        performance.groupby("category_id", as_index=False)
        .agg(baseline_uplift_pct=("promo_uplift_pct", "mean"), adjusted_uplift_pct=("promo_uplift_pct", "mean"))
        .merge(products.drop_duplicates("category_id")[["category_id", "category_name"]], on="category_id", how="left")
    )
    category["adjusted_pvalue"] = 0.5
    category["adjusted_qvalue"] = 0.5
    category["direction"] = category["adjusted_uplift_pct"].apply(lambda value: "up" if value > 0 else "down")
    category["diagnostic_status"] = "naive_unadjusted"
    category[
        [
            "category_id",
            "category_name",
            "baseline_uplift_pct",
            "adjusted_uplift_pct",
            "adjusted_pvalue",
            "adjusted_qvalue",
            "direction",
            "diagnostic_status",
        ]
    ].to_csv(output / "category_uplift.tsv", sep="\t", index=False)
    risk = pd.DataFrame(
        {
            "store_id": stores["store_id"],
            "return_rate": 0.0,
            "duplicate_rate": 0.0,
            "stockout_exposure_hours": 0.0,
            "weather_anomaly_days": 0,
            "traffic_anomaly_days": 0,
            "final_risk_level": "low",
        }
    )
    risk.to_csv(output / "store_risk_audit.tsv", sep="\t", index=False)
    performance.assign(diagnostic_status="naive_unadjusted").to_csv(output / "analysis_diagnostics.tsv", sep="\t", index=False)
    category.assign(metric="adjusted_uplift_pct", value=category["adjusted_uplift_pct"]).to_csv(
        output / "figures" / "promo_roi_by_category.csv", index=False
    )
    risk.melt(id_vars=["store_id"], var_name="risk_factor", value_name="value").to_csv(
        output / "figures" / "store_risk_matrix.csv", index=False
    )
    report = {
        "analysis_window": {"min_business_date": "2026-03-08", "max_business_date": "2026-03-31"},
        "n_promotions": int(promos["promo_id"].nunique()),
        "n_store_promo_category_rows": int(len(performance)),
        "n_reportable_rows": int(performance["reportable"].sum()),
        "top_promotions": performance.sort_values("adjusted_roi", ascending=False).head(5).to_dict("records"),
        "category_summary": category.to_dict("records"),
        "risk_summary": risk.groupby("final_risk_level").size().to_dict(),
        "model_summary": {
            "baseline_formula": "UTC naive revenue comparison",
            "adjusted_formula": "not implemented",
            "controlled_factors": [],
        },
        "enrichment_summary": {"service": "not_called"},
        "notes": ["Broken starting point."],
    }
    (output / "promo_summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
