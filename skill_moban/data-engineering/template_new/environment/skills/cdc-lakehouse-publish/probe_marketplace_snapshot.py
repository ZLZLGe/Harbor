#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import requests


DATA_ROOT = Path("/app/workspace/data/raw")
WAREHOUSE_PATH = Path("/app/output/warehouse.duckdb")
API_URL = "http://127.0.0.1:8331"
SERVICE_PATH = Path("/services/audit-service/server.pyc")
ALT_ROOT = Path("/tests/fixtures_alt/raw")


def _coerce(value: object) -> datetime:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def parse_naive(value: object) -> datetime:
    return _coerce(value).replace(tzinfo=None)


def parse_utc(value: object) -> datetime:
    parsed = _coerce(value)
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _normalize_gross(row: pd.Series) -> float:
    gross_usd = str(row.get("gross_total_usd", "")).strip()
    cents = str(row.get("gross_total_cents", "")).strip()
    if cents:
        return round(int(cents) / 100.0, 2)
    if gross_usd:
        return round(float(gross_usd), 2)
    return 0.0


def _reference_tables(data_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    orders = pd.read_json(data_root / "orders_cdc.jsonl", lines=True, dtype=False)
    shipments = pd.read_json(data_root / "shipment_events.jsonl", lines=True, dtype=False)
    refunds = pd.read_csv(data_root / "refunds.csv")
    sellers = pd.read_csv(data_root / "sellers.csv")
    catalog = pd.read_csv(data_root / "catalog.csv")

    orders["line_id"] = orders["line_id"].astype(int)
    orders["event_seq"] = orders["event_seq"].astype(int)
    orders["quantity"] = orders["quantity"].astype(int)
    orders["ingested_dt"] = orders["ingested_at"].map(parse_utc)
    orders["ordered_dt"] = orders["ordered_at"].map(parse_utc)
    orders = orders.sort_values(
        ["order_id", "line_id", "event_seq", "ingested_dt"],
        ascending=[True, True, False, False],
    )
    final_orders = orders.drop_duplicates(["order_id", "line_id"], keep="first").copy()
    final_orders["gross_revenue_usd"] = final_orders.apply(_normalize_gross, axis=1)
    final_orders["snapshot_date"] = final_orders["ordered_dt"].dt.strftime("%Y-%m-%d")

    shipments["line_id"] = shipments["line_id"].astype(int)
    shipments["event_dt"] = shipments["event_ts"].map(parse_utc)
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
    return seller_daily, sku_fulfillment


def _frame_hash(frame: pd.DataFrame) -> str:
    csv_text = frame.to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(csv_text.encode("utf-8")).hexdigest()


def _load_table(table_name: str, order_by: list[str]) -> pd.DataFrame:
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as conn:
        return conn.execute(
            f"SELECT * FROM {table_name} ORDER BY {', '.join(order_by)}"
        ).fetchdf()


def _pretty(title: str, payload: object) -> None:
    print(f"{title}:")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def ensure_service(api_url: str = API_URL) -> None:
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            return
    except requests.RequestException:
        pass

    subprocess.Popen(
        ["python3", str(SERVICE_PATH)],
        stdout=open("/tmp/marketplace-audit.log", "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(40):
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError("publish audit service did not start")


def main() -> None:
    ensure_service(API_URL)
    manifest = requests.get(f"{API_URL}/manifest", timeout=30).json()
    summary: dict[str, object] = {"manifest": manifest}

    orders = pd.read_json(DATA_ROOT / "orders_cdc.jsonl", lines=True, dtype=False)
    orders["line_id"] = orders["line_id"].astype(int)
    orders["event_seq"] = orders["event_seq"].astype(int)
    orders["updated_dt"] = orders["updated_at"].map(parse_utc)
    orders["ingested_dt"] = orders["ingested_at"].map(parse_utc)

    seq_latest = (
        orders.sort_values(["order_id", "line_id", "event_seq", "ingested_dt"], ascending=[True, True, False, False])
        .drop_duplicates(["order_id", "line_id"], keep="first")
        .set_index(["order_id", "line_id"])
    )
    updated_latest = (
        orders.sort_values(["order_id", "line_id", "updated_dt", "ingested_dt"], ascending=[True, True, False, False])
        .drop_duplicates(["order_id", "line_id"], keep="first")
        .set_index(["order_id", "line_id"])
    )
    mismatches = []
    for key in seq_latest.index:
        seq_row = seq_latest.loc[key]
        upd_row = updated_latest.loc[key]
        if int(seq_row["event_seq"]) != int(upd_row["event_seq"]):
            mismatches.append(
                {
                    "order_id": key[0],
                    "line_id": int(key[1]),
                    "seq_event_seq": int(seq_row["event_seq"]),
                    "updated_event_seq": int(upd_row["event_seq"]),
                }
            )
    summary["replay_conflicts"] = {
        "count": len(mismatches),
        "examples": mismatches[:5],
    }

    amount_drift = orders.loc[
        orders["gross_total_cents"].fillna("").astype(str).str.strip().ne(""),
        ["order_id", "line_id", "event_seq", "gross_total_usd", "gross_total_cents"],
    ].copy()
    if not amount_drift.empty:
        amount_drift["normalized_usd"] = amount_drift["gross_total_cents"].astype(int) / 100.0
    amount_examples = amount_drift.to_dict(orient="records")
    summary["amount_drift_examples"] = {
        "count": len(amount_examples),
        "examples": amount_examples[:5],
    }

    shipments = pd.read_json(DATA_ROOT / "shipment_events.jsonl", lines=True, dtype=False)
    shipments["line_id"] = shipments["line_id"].astype(int)
    shipped = shipments.loc[shipments["event_type"].eq("shipped")].copy()
    shipped = shipped.sort_values(["order_id", "line_id", "event_ts"]).drop_duplicates(["order_id", "line_id"])
    final_orders = seq_latest.reset_index()
    merged = final_orders.merge(shipped[["order_id", "line_id", "event_ts"]], on=["order_id", "line_id"], how="inner")

    flips = []
    sellers = pd.read_csv(DATA_ROOT / "sellers.csv")
    merged = merged.merge(sellers, on="seller_id", how="left")
    for _, row in merged.iterrows():
        aware_hours = (parse_utc(row["event_ts"]) - parse_utc(row["ordered_at"])).total_seconds() / 3600.0
        naive_hours = (parse_naive(row["event_ts"]) - parse_naive(row["ordered_at"])).total_seconds() / 3600.0
        aware_on_time = aware_hours <= float(row["sla_hours"])
        naive_on_time = naive_hours <= float(row["sla_hours"])
        if aware_on_time != naive_on_time:
            flips.append(
                {
                    "order_id": row["order_id"],
                    "line_id": int(row["line_id"]),
                    "aware_hours": round(aware_hours, 3),
                    "naive_hours": round(naive_hours, 3),
                    "sla_hours": float(row["sla_hours"]),
                }
            )
    summary["timezone_sla_flips"] = {
        "count": len(flips),
        "examples": flips[:5],
    }

    if WAREHOUSE_PATH.exists():
        expected_daily, expected_sku = _reference_tables(DATA_ROOT)
        actual_daily = _load_table("seller_daily_mart", ["snapshot_date", "seller_id"])
        actual_sku = _load_table("sku_fulfillment_mart", ["snapshot_date", "seller_id", "sku"])
        summary["warehouse_check"] = {
            "seller_daily_mart": {
                "matches": actual_daily.equals(expected_daily),
                "actual_rows": int(len(actual_daily)),
                "expected_rows": int(len(expected_daily)),
                "actual_sha256": _frame_hash(actual_daily),
                "expected_sha256": _frame_hash(expected_daily),
            },
            "sku_fulfillment_mart": {
                "matches": actual_sku.equals(expected_sku),
                "actual_rows": int(len(actual_sku)),
                "expected_rows": int(len(expected_sku)),
                "actual_sha256": _frame_hash(actual_sku),
                "expected_sha256": _frame_hash(expected_sku),
            },
        }

    if ALT_ROOT.exists():
        from marketplace_snapshot.pipeline import build_warehouse

        alt_warehouse = Path("/tmp/marketplace-alt-skill-check.duckdb")
        if alt_warehouse.exists():
            alt_warehouse.unlink()
        build_warehouse(data_root=ALT_ROOT, warehouse_path=alt_warehouse)

        expected_daily, expected_sku = _reference_tables(ALT_ROOT)
        with duckdb.connect(str(alt_warehouse), read_only=True) as conn:
            alt_daily = conn.execute(
                "SELECT * FROM seller_daily_mart ORDER BY snapshot_date, seller_id"
            ).fetchdf()
            alt_sku = conn.execute(
                "SELECT * FROM sku_fulfillment_mart ORDER BY snapshot_date, seller_id, sku"
            ).fetchdf()
        summary["alt_fixture_check"] = {
            "seller_daily_mart": {
                "matches": alt_daily.equals(expected_daily),
                "actual_sha256": _frame_hash(alt_daily),
                "expected_sha256": _frame_hash(expected_daily),
            },
            "sku_fulfillment_mart": {
                "matches": alt_sku.equals(expected_sku),
                "actual_sha256": _frame_hash(alt_sku),
                "expected_sha256": _frame_hash(expected_sku),
            },
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
