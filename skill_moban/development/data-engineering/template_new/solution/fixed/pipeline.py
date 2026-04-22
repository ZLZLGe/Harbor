from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .common import WAREHOUSE_PATH, ensure_output_root, parse_timestamp_utc


def _load_jsonl(path: Path) -> pd.DataFrame:
    return pd.read_json(path, lines=True, dtype=False)


def _normalize_amount(row: pd.Series) -> float:
    cents = str(row.get("gross_total_cents", "")).strip()
    gross_usd = str(row.get("gross_total_usd", "")).strip()
    if cents:
        return round(int(cents) / 100.0, 2)
    if gross_usd:
        return round(float(gross_usd), 2)
    return 0.0


def build_warehouse(
    data_root: Path = Path("/app/workspace/data/raw"),
    warehouse_path: Path = WAREHOUSE_PATH,
) -> dict:
    ensure_output_root()
    orders = _load_jsonl(data_root / "orders_cdc.jsonl")
    shipments = _load_jsonl(data_root / "shipment_events.jsonl")
    refunds = pd.read_csv(data_root / "refunds.csv")
    sellers = pd.read_csv(data_root / "sellers.csv")
    catalog = pd.read_csv(data_root / "catalog.csv")

    orders["line_id"] = orders["line_id"].astype(int)
    orders["event_seq"] = orders["event_seq"].astype(int)
    orders["quantity"] = orders["quantity"].astype(int)
    orders["ingested_dt"] = orders["ingested_at"].map(parse_timestamp_utc)
    orders["ordered_dt"] = orders["ordered_at"].map(parse_timestamp_utc)
    orders = orders.sort_values(
        ["order_id", "line_id", "event_seq", "ingested_dt"],
        ascending=[True, True, False, False],
    )
    final_orders = orders.drop_duplicates(["order_id", "line_id"], keep="first").copy()
    final_orders["gross_revenue_usd"] = final_orders.apply(_normalize_amount, axis=1)
    final_orders["snapshot_date"] = final_orders["ordered_dt"].dt.strftime("%Y-%m-%d")

    shipments["line_id"] = shipments["line_id"].astype(int)
    shipments["event_dt"] = shipments["event_ts"].map(parse_timestamp_utc)
    shipped = (
        shipments.loc[shipments["event_type"].eq("shipped"), ["order_id", "line_id", "event_dt"]]
        .sort_values(["order_id", "line_id", "event_dt"])
        .drop_duplicates(["order_id", "line_id"], keep="first")
        .rename(columns={"event_dt": "shipped_dt"})
    )
    delivered = (
        shipments.loc[shipments["event_type"].eq("delivered"), ["order_id", "line_id"]]
        .drop_duplicates()
        .assign(delivered_flag=1)
    )
    shipment_facts = shipped.merge(delivered, on=["order_id", "line_id"], how="left").fillna({"delivered_flag": 0})

    refunds["line_id"] = refunds["line_id"].astype(int)
    refunds["refunded_usd"] = refunds["refunded_usd"].astype(float)
    refund_facts = (
        refunds.groupby(["order_id", "line_id"], as_index=False)
        .agg(refunded_lines=("refund_id", "nunique"), refunded_revenue_usd=("refunded_usd", "sum"))
    )

    mart = (
        final_orders.merge(shipment_facts, on=["order_id", "line_id"], how="left")
        .merge(refund_facts, on=["order_id", "line_id"], how="left")
        .merge(sellers, on="seller_id", how="left")
        .merge(catalog, on="sku", how="left")
    )
    mart["delivered_flag"] = mart["delivered_flag"].fillna(0).astype(int)
    mart["refunded_lines"] = mart["refunded_lines"].fillna(0).astype(int)
    mart["refunded_revenue_usd"] = mart["refunded_revenue_usd"].fillna(0.0)
    mart["hours_to_ship"] = (
        (mart["shipped_dt"] - mart["ordered_dt"]).dt.total_seconds() / 3600.0
    )
    mart["shipped_flag"] = (
        mart["shipped_dt"].notna() & mart["order_status"].ne("cancelled")
    ).astype(int)
    mart["completed_flag"] = mart["order_status"].eq("completed").astype(int)
    mart["cancelled_flag"] = mart["order_status"].eq("cancelled").astype(int)
    mart["on_time_flag"] = (
        mart["shipped_dt"].notna() & (mart["hours_to_ship"] <= mart["sla_hours"])
    ).astype(int)
    mart["effective_gross_revenue_usd"] = (
        mart["gross_revenue_usd"] * mart["completed_flag"]
    )
    mart["net_revenue_usd"] = mart["effective_gross_revenue_usd"] - mart["refunded_revenue_usd"]

    seller_daily = (
        mart.groupby(["snapshot_date", "seller_id", "seller_name"], as_index=False)
        .agg(
            order_lines=("order_id", "count"),
            completed_lines=("completed_flag", "sum"),
            cancelled_lines=("cancelled_flag", "sum"),
            shipped_lines=("shipped_flag", "sum"),
            on_time_shipments=("on_time_flag", "sum"),
            refunded_lines=("refunded_lines", "sum"),
            gross_revenue_usd=("effective_gross_revenue_usd", "sum"),
            refunded_revenue_usd=("refunded_revenue_usd", "sum"),
            net_revenue_usd=("net_revenue_usd", "sum"),
            avg_hours_to_ship=("hours_to_ship", "mean"),
        )
        .fillna({"avg_hours_to_ship": 0.0})
        .sort_values(["snapshot_date", "seller_id"])
        .reset_index(drop=True)
    )
    seller_daily["gross_revenue_usd"] = seller_daily["gross_revenue_usd"].round(2)
    seller_daily["refunded_revenue_usd"] = seller_daily["refunded_revenue_usd"].round(2)
    seller_daily["net_revenue_usd"] = seller_daily["net_revenue_usd"].round(2)
    seller_daily["avg_hours_to_ship"] = seller_daily["avg_hours_to_ship"].round(3)

    sku_fulfillment = (
        mart.groupby(["snapshot_date", "seller_id", "sku", "category"], as_index=False)
        .agg(
            completed_lines=("completed_flag", "sum"),
            shipped_lines=("shipped_flag", "sum"),
            delivered_lines=("delivered_flag", "sum"),
            refunded_lines=("refunded_lines", "sum"),
            net_revenue_usd=("net_revenue_usd", "sum"),
            on_time_shipments=("on_time_flag", "sum"),
        )
        .sort_values(["snapshot_date", "seller_id", "sku"])
        .reset_index(drop=True)
    )
    sku_fulfillment["net_revenue_usd"] = sku_fulfillment["net_revenue_usd"].round(2)
    sku_fulfillment["on_time_ship_rate"] = sku_fulfillment.apply(
        lambda row: 0.0
        if int(row["shipped_lines"]) == 0
        else round(float(row["on_time_shipments"]) / float(row["shipped_lines"]), 4),
        axis=1,
    )
    sku_fulfillment = sku_fulfillment.drop(columns=["on_time_shipments"])

    with duckdb.connect(str(warehouse_path)) as conn:
        conn.execute("DROP TABLE IF EXISTS seller_daily_mart")
        conn.execute("DROP TABLE IF EXISTS sku_fulfillment_mart")
        conn.register("seller_daily_df", seller_daily)
        conn.register("sku_fulfillment_df", sku_fulfillment)
        conn.execute("CREATE TABLE seller_daily_mart AS SELECT * FROM seller_daily_df")
        conn.execute("CREATE TABLE sku_fulfillment_mart AS SELECT * FROM sku_fulfillment_df")

    return {
        "warehouse_path": str(warehouse_path),
        "seller_daily_rows": int(len(seller_daily)),
        "sku_fulfillment_rows": int(len(sku_fulfillment)),
    }
