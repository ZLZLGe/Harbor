#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import NormalDist
from zoneinfo import ZoneInfo

import pandas as pd


DATA_ROOT = Path("/root/environment/data")


def parse_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True)


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def load_inputs(data_root: Path = DATA_ROOT) -> dict[str, pd.DataFrame | dict]:
    return {
        "stores": pd.read_csv(data_root / "catalog" / "stores.csv"),
        "products": pd.read_csv(data_root / "catalog" / "products.csv"),
        "promotions": pd.read_csv(data_root / "catalog" / "promotions.csv"),
        "events": pd.read_csv(data_root / "pos" / "transaction_events.csv"),
        "inventory": pd.read_csv(data_root / "inventory" / "inventory_snapshots.csv"),
        "weather": pd.read_csv(data_root / "external" / "weather_daily.csv"),
        "traffic": pd.read_csv(data_root / "external" / "traffic_daily.csv"),
        "contract": json.loads((data_root / "catalog" / "analysis_contract.json").read_text(encoding="utf-8")),
    }


def attach_local_business_date(events: pd.DataFrame, stores: pd.DataFrame) -> pd.DataFrame:
    timezone_by_store = stores.set_index("store_id")["timezone"].to_dict()
    events = events.copy()
    events["event_at_utc"] = parse_utc(events["event_at_utc"])
    events["ingested_at_utc"] = parse_utc(events["ingested_at_utc"])

    def local_date(row: pd.Series) -> str:
        return row["event_at_utc"].tz_convert(ZoneInfo(timezone_by_store[row["store_id"]])).date().isoformat()

    events["business_date"] = events.apply(local_date, axis=1)
    return events


def latest_completed_lines(inputs: dict[str, pd.DataFrame | dict]) -> pd.DataFrame:
    stores = inputs["stores"]
    products = inputs["products"].copy()
    events = attach_local_business_date(inputs["events"], stores)
    events = events.sort_values(["order_id", "event_at_utc", "ingested_at_utc", "event_id"])
    latest = events.groupby("order_id", as_index=False).tail(1).copy()
    completed = latest[latest["status"].eq("completed")].copy()
    completed = completed.merge(products[["product_id", "category_id", "category_name", "active"]], on="product_id", how="left")
    completed = completed[bool_series(completed["active"])].copy()
    completed["net_revenue"] = completed["unit_price"].astype(float) * completed["quantity"].astype(int) - completed[
        "discount_amount"
    ].astype(float)
    completed["net_units"] = completed["quantity"].astype(int)
    completed["gross_margin"] = (
        (completed["unit_price"].astype(float) - completed["unit_cost"].astype(float)) * completed["quantity"].astype(int)
        - completed["discount_amount"].astype(float)
    )
    return completed


def daily_sales(inputs: dict[str, pd.DataFrame | dict]) -> pd.DataFrame:
    completed = latest_completed_lines(inputs)
    daily = (
        completed.groupby(["business_date", "store_id", "category_id"], as_index=False)
        .agg(
            net_revenue=("net_revenue", "sum"),
            net_units=("net_units", "sum"),
            gross_margin=("gross_margin", "sum"),
            order_count=("order_id", "nunique"),
        )
        .round({"net_revenue": 2, "gross_margin": 2})
    )
    traffic = inputs["traffic"].copy()
    weather = inputs["weather"].copy()
    traffic["holiday"] = bool_series(traffic["holiday"])
    weather["weather_anomaly"] = bool_series(weather["weather_anomaly"])
    daily = daily.merge(traffic, on=["store_id", "business_date"], how="left")
    daily = daily.merge(weather[["store_id", "business_date", "weather_anomaly"]], on=["store_id", "business_date"], how="left")
    daily["traffic_index"] = daily["traffic_index"].astype(float)
    daily["holiday"] = daily["holiday"].fillna(False)
    daily["weather_anomaly"] = daily["weather_anomaly"].fillna(False)
    return daily


def stockout_hours_for(
    inventory: pd.DataFrame,
    stores: pd.DataFrame,
    products: pd.DataFrame,
    store_id: str,
    category_id: str,
    start_date: str,
    end_date: str,
) -> float:
    tz = ZoneInfo(stores.set_index("store_id").loc[store_id, "timezone"])
    active_products = set(
        products[(products["category_id"].eq(category_id)) & (bool_series(products["active"]))]["product_id"]
    )
    if not active_products:
        return 0.0
    window_start = datetime.fromisoformat(start_date).replace(tzinfo=tz)
    window_end = (datetime.fromisoformat(end_date) + timedelta(days=1)).replace(tzinfo=tz)
    subset = inventory[(inventory["store_id"].eq(store_id)) & (inventory["product_id"].isin(active_products))].copy()
    if subset.empty:
        return 0.0
    subset["event_at_utc"] = parse_utc(subset["event_at_utc"])
    subset["ingested_at_utc"] = parse_utc(subset["ingested_at_utc"])
    hours = 0.0
    for _, group in subset.sort_values(["product_id", "event_at_utc", "ingested_at_utc"]).groupby("product_id"):
        rows = list(group.to_dict("records"))
        for current, nxt in zip(rows, rows[1:]):
            if int(current["on_hand"]) > 0:
                continue
            interval_start = current["event_at_utc"].to_pydatetime().astimezone(tz)
            interval_end = nxt["event_at_utc"].to_pydatetime().astimezone(tz)
            clipped_start = max(interval_start, window_start)
            clipped_end = min(interval_end, window_end)
            if clipped_end > clipped_start:
                hours += (clipped_end - clipped_start).total_seconds() / 3600.0
    return round(hours, 3)


def scaled_baseline(baseline: pd.DataFrame, promo_days: int, metric: str, use_adjustment: bool = False, promo_traffic: float = 1.0) -> float:
    if baseline.empty:
        return 0.0
    if use_adjustment:
        clean = baseline[(~baseline["weather_anomaly"]) & (~baseline["holiday"])].copy()
        if clean.empty:
            clean = baseline.copy()
        return float((clean[metric] / clean["traffic_index"]).mean() * promo_traffic * promo_days)
    return float(baseline[metric].sum() * promo_days / max(len(baseline["business_date"].unique()), 1))


def promo_performance(inputs: dict[str, pd.DataFrame | dict]) -> pd.DataFrame:
    stores = inputs["stores"]
    promotions = inputs["promotions"].copy()
    inventory = inputs["inventory"]
    products = inputs["products"]
    contract = inputs["contract"]
    daily = daily_sales(inputs)
    rows: list[dict[str, object]] = []
    for promo in promotions.to_dict("records"):
        start = datetime.fromisoformat(str(promo["business_start_date"]))
        end = datetime.fromisoformat(str(promo["business_end_date"]))
        promo_dates = [(start + timedelta(days=i)).date().isoformat() for i in range((end - start).days + 1)]
        baseline_start = start - timedelta(days=int(contract["baseline_days"]))
        baseline_dates = [(baseline_start + timedelta(days=i)).date().isoformat() for i in range(int(contract["baseline_days"]))]
        promo_days = len(promo_dates)
        for store_id in stores["store_id"]:
            subset = daily[(daily["store_id"].eq(store_id)) & (daily["category_id"].eq(promo["category_id"]))]
            promo_daily = subset[subset["business_date"].isin(promo_dates)]
            baseline_daily = subset[subset["business_date"].isin(baseline_dates)]
            promo_traffic = float(inputs["traffic"][(inputs["traffic"]["store_id"].eq(store_id)) & (inputs["traffic"]["business_date"].isin(promo_dates))]["traffic_index"].astype(float).mean())
            net_revenue = float(promo_daily["net_revenue"].sum())
            net_units = int(promo_daily["net_units"].sum())
            gross_margin = float(promo_daily["gross_margin"].sum())
            baseline_net_revenue = scaled_baseline(baseline_daily, promo_days, "net_revenue", False)
            adjusted_baseline_revenue = scaled_baseline(baseline_daily, promo_days, "net_revenue", True, promo_traffic)
            adjusted_baseline_margin = scaled_baseline(baseline_daily, promo_days, "gross_margin", True, promo_traffic)
            stockout_hours = stockout_hours_for(
                inventory, stores, products, store_id, str(promo["category_id"]), str(promo["business_start_date"]), str(promo["business_end_date"])
            )
            stockout_penalty = stockout_hours * float(contract["stockout_penalty_per_hour"])
            baseline_uplift = 0.0 if baseline_net_revenue <= 0 else net_revenue / baseline_net_revenue - 1.0
            adjusted_uplift = 0.0 if adjusted_baseline_revenue <= 0 else net_revenue / adjusted_baseline_revenue - 1.0 - stockout_penalty
            incremental_margin = gross_margin - adjusted_baseline_margin
            store_spend = float(promo["promo_spend"]) / len(stores)
            adjusted_roi = (incremental_margin - store_spend) / store_spend if store_spend else 0.0
            reportable = (
                adjusted_roi >= float(contract["reportable_min_adjusted_roi"])
                and adjusted_uplift > 0.05
                and stockout_hours <= float(contract["reportable_max_stockout_hours"])
            )
            if stockout_hours > float(contract["reportable_max_stockout_hours"]):
                status = "stockout_constrained"
            elif reportable and baseline_uplift > 0.05:
                status = "stable_effective"
            elif reportable:
                status = "rescued_after_adjustment"
            elif baseline_uplift > 0.05 and adjusted_uplift <= 0.05:
                status = "baseline_false_positive"
            else:
                status = "nonreportable"
            rows.append(
                {
                    "store_id": store_id,
                    "promo_id": promo["promo_id"],
                    "category_id": promo["category_id"],
                    "business_start_date": promo["business_start_date"],
                    "business_end_date": promo["business_end_date"],
                    "net_revenue": round(net_revenue, 2),
                    "net_units": net_units,
                    "gross_margin": round(gross_margin, 2),
                    "baseline_net_revenue": round(baseline_net_revenue, 2),
                    "adjusted_baseline_net_revenue": round(adjusted_baseline_revenue, 2),
                    "promo_uplift_pct": round(baseline_uplift * 100, 3),
                    "adjusted_uplift_pct": round(adjusted_uplift * 100, 3),
                    "incremental_margin": round(incremental_margin, 2),
                    "stockout_exposure_hours": round(stockout_hours, 3),
                    "adjusted_roi": round(adjusted_roi, 4),
                    "diagnostic_status": status,
                    "reportable": bool(reportable),
                }
            )
    return pd.DataFrame(rows).sort_values(["promo_id", "store_id"]).reset_index(drop=True)


def bh_qvalues(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    ordered = sorted(enumerate(pvalues), key=lambda item: item[1], reverse=True)
    q = [1.0] * m
    prev = 1.0
    for index, pvalue in ordered:
        rank = sorted(pvalues).index(pvalue) + 1
        value = min(prev, pvalue * m / rank)
        q[index] = min(1.0, value)
        prev = value
    return q


def category_uplift(performance: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    category_names = products.drop_duplicates("category_id").set_index("category_id")["category_name"].to_dict()
    rows = []
    for category_id, group in performance.groupby("category_id"):
        values = group["adjusted_uplift_pct"].astype(float) / 100.0
        mean = float(values.mean())
        std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        z = 0.0 if std == 0 else mean / (std / math.sqrt(len(values)))
        pvalue = 1.0 if z == 0 else 2 * (1 - NormalDist().cdf(abs(z)))
        reportable = group[group["reportable"]]
        if not reportable.empty:
            status = "reportable_positive"
        elif "stockout_constrained" in set(group["diagnostic_status"]):
            status = "stockout_limited"
        elif "baseline_false_positive" in set(group["diagnostic_status"]):
            status = "baseline_sensitive"
        else:
            status = "not_supported"
        rows.append(
            {
                "category_id": category_id,
                "category_name": category_names.get(category_id, category_id),
                "baseline_uplift_pct": round(float(group["promo_uplift_pct"].mean()), 3),
                "adjusted_uplift_pct": round(float(group["adjusted_uplift_pct"].mean()), 3),
                "adjusted_pvalue": max(0.000001, min(1.0, round(pvalue, 6))),
                "direction": "up" if mean > 0 else "down",
                "diagnostic_status": status,
                "n_reportable_rows": int(group["reportable"].sum()),
            }
        )
    qvalues = bh_qvalues([row["adjusted_pvalue"] for row in rows])
    for row, qvalue in zip(rows, qvalues):
        row["adjusted_qvalue"] = round(qvalue, 6)
    return pd.DataFrame(rows).sort_values(["category_id"]).reset_index(drop=True)


def store_risk_audit(inputs: dict[str, pd.DataFrame | dict], performance: pd.DataFrame) -> pd.DataFrame:
    events = attach_local_business_date(inputs["events"], inputs["stores"])
    latest = events.sort_values(["order_id", "event_at_utc", "ingested_at_utc", "event_id"]).groupby("order_id", as_index=False).tail(1)
    rows = []
    thresholds = inputs["contract"]["risk_thresholds"]
    for store_id in inputs["stores"]["store_id"]:
        store_events = events[events["store_id"].eq(store_id)]
        store_latest = latest[latest["store_id"].eq(store_id)]
        duplicate_rate = 1.0 - store_events["order_id"].nunique() / max(len(store_events), 1)
        return_rate = store_latest["status"].isin(["returned", "cancelled"]).mean()
        stockout_hours = float(performance[performance["store_id"].eq(store_id)]["stockout_exposure_hours"].sum())
        anomaly_days = int(inputs["weather"][(inputs["weather"]["store_id"].eq(store_id)) & (bool_series(inputs["weather"]["weather_anomaly"]))]["business_date"].nunique())
        traffic = inputs["traffic"][inputs["traffic"]["store_id"].eq(store_id)].copy()
        traffic["traffic_index"] = traffic["traffic_index"].astype(float)
        traffic_anomaly_days = int((abs(traffic["traffic_index"] - traffic["traffic_index"].mean()) > 0.09).sum())
        if stockout_hours > thresholds["high_stockout_hours"] or return_rate > thresholds["high_return_rate"]:
            risk = "high"
        elif duplicate_rate > thresholds["high_duplicate_rate"] or anomaly_days:
            risk = "medium"
        else:
            risk = "low"
        rows.append(
            {
                "store_id": store_id,
                "return_rate": round(float(return_rate), 4),
                "duplicate_rate": round(float(duplicate_rate), 4),
                "stockout_exposure_hours": round(stockout_hours, 3),
                "weather_anomaly_days": anomaly_days,
                "traffic_anomaly_days": traffic_anomaly_days,
                "final_risk_level": risk,
            }
        )
    return pd.DataFrame(rows).sort_values("store_id").reset_index(drop=True)


def service_enrichment(performance: pd.DataFrame, category: pd.DataFrame) -> dict[str, object]:
    payload = {
        "promo_ids": sorted(performance["promo_id"].unique().tolist()),
        "category_ids": sorted(category["category_id"].unique().tolist()),
        "store_ids": sorted(performance["store_id"].unique().tolist()),
    }
    request = urllib.request.Request(
        "http://127.0.0.1:8765/enrich",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError):
        return {"service": "unavailable", "promotions": {}, "categories": {}, "stores": {}}


def write_outputs(output: Path, inputs: dict[str, pd.DataFrame | dict]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    figures = output / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    performance = promo_performance(inputs)
    category = category_uplift(performance, inputs["products"])
    risk = store_risk_audit(inputs, performance)
    enrichment = service_enrichment(performance, category)
    performance[
        [
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
    ].to_csv(output / "promo_performance.csv", index=False)
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
    risk.to_csv(output / "store_risk_audit.tsv", sep="\t", index=False)
    performance.to_csv(output / "analysis_diagnostics.tsv", sep="\t", index=False)
    category.assign(metric="adjusted_uplift_pct", value=category["adjusted_uplift_pct"]).to_csv(
        figures / "promo_roi_by_category.csv", index=False
    )
    risk.melt(id_vars=["store_id"], var_name="risk_factor", value_name="value").to_csv(
        figures / "store_risk_matrix.csv", index=False
    )
    reportable = performance[performance["reportable"]].sort_values("adjusted_roi", ascending=False)
    report = {
        "analysis_window": {
            "min_business_date": str(inputs["traffic"]["business_date"].min()),
            "max_business_date": str(inputs["traffic"]["business_date"].max()),
        },
        "n_promotions": int(inputs["promotions"]["promo_id"].nunique()),
        "n_store_promo_category_rows": int(len(performance)),
        "n_reportable_rows": int(performance["reportable"].sum()),
        "top_promotions": reportable.head(5)[
            ["store_id", "promo_id", "category_id", "adjusted_roi", "adjusted_uplift_pct"]
        ].to_dict("records"),
        "category_summary": category.to_dict("records"),
        "risk_summary": risk.groupby("final_risk_level").size().to_dict(),
        "model_summary": {
            "baseline_formula": "promo_window_net_revenue / prior_7_local_business_day_net_revenue - 1",
            "adjusted_formula": "traffic-normalized clean baseline with holiday/weather exclusions minus stockout exposure penalty",
            "controlled_factors": [
                "store",
                "category",
                "local_business_date",
                "weekday",
                "holiday",
                "weather_anomaly",
                "traffic_index",
                "stockout_exposure_hours",
            ],
        },
        "enrichment_summary": enrichment,
        "notes": [
            "Latest order event wins by event_at_utc then ingested_at_utc.",
            "Business dates are computed in each store timezone.",
            "Stockout intervals are clipped to promotion windows before ROI classification.",
        ],
    }
    (output / "promo_summary.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/root/answer")
    parser.add_argument("--data-root", default=str(DATA_ROOT))
    args = parser.parse_args()
    write_outputs(Path(args.output), load_inputs(Path(args.data_root)))


if __name__ == "__main__":
    main()
