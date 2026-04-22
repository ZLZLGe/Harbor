from __future__ import annotations

from pathlib import Path

import requests

from conftest import (
    API_URL,
    BUNDLE_PATH,
    DATA_ROOT,
    LAST_PUBLISH_PATH,
    RECEIPT_PATH,
    TESTS_ROOT,
    TRACE_PATH,
    WAREHOUSE_PATH,
    build_and_publish,
    canonical_json_sha,
    ensure_service,
    load_json,
    load_jsonl,
    load_table,
    running_audit_service,
)


SELLER_DAILY_COLUMNS = [
    "snapshot_date",
    "seller_id",
    "seller_name",
    "order_lines",
    "completed_lines",
    "cancelled_lines",
    "shipped_lines",
    "on_time_shipments",
    "refunded_lines",
    "gross_revenue_usd",
    "refunded_revenue_usd",
    "net_revenue_usd",
    "avg_hours_to_ship",
]
SKU_COLUMNS = [
    "snapshot_date",
    "seller_id",
    "sku",
    "category",
    "completed_lines",
    "shipped_lines",
    "delivered_lines",
    "refunded_lines",
    "net_revenue_usd",
    "on_time_ship_rate",
]


def test_a_output_files_and_table_shapes_exist() -> None:
    ensure_service()
    assert WAREHOUSE_PATH.exists(), "Missing /app/output/warehouse.duckdb"
    assert BUNDLE_PATH.exists(), "Missing /app/output/publish_bundle.json"
    assert RECEIPT_PATH.exists(), "Missing /app/output/publish_receipt.json"

    seller_daily = load_table(WAREHOUSE_PATH, "seller_daily_mart", ["snapshot_date", "seller_id"])
    sku_fulfillment = load_table(WAREHOUSE_PATH, "sku_fulfillment_mart", ["snapshot_date", "seller_id", "sku"])
    assert list(seller_daily.columns) == SELLER_DAILY_COLUMNS
    assert list(sku_fulfillment.columns) == SKU_COLUMNS
    assert len(seller_daily) >= 5
    assert len(sku_fulfillment) >= 7

    bundle = load_json(BUNDLE_PATH)
    receipt = load_json(RECEIPT_PATH)
    assert set(bundle.keys()) >= {"snapshot_id", "contract_version", "warehouse_path", "tables"}
    assert set(receipt.keys()) >= {"request_sha256", "accepted", "snapshot_id", "status", "accepted_tables"}
    assert bundle["warehouse_path"] == "/app/output/warehouse.duckdb"
    assert receipt["accepted"] is True
    assert receipt["status"] == "accepted"
    assert receipt["accepted_tables"] == 2


def test_b_solver_used_live_manifest_and_publish_chain() -> None:
    bundle = load_json(BUNDLE_PATH)
    receipt = load_json(RECEIPT_PATH)
    last_publish = load_json(LAST_PUBLISH_PATH)
    trace_lines = load_jsonl(TRACE_PATH)

    bundle_hash = canonical_json_sha(bundle)
    assert receipt["request_sha256"] == bundle_hash
    assert last_publish["payload_sha256"] == bundle_hash
    assert last_publish["accepted"] is True

    manifest_seen = any(entry.get("event") == "manifest" for entry in trace_lines)
    publish_seen = any(
        entry.get("event") == "publish" and entry.get("payload_sha256") == bundle_hash
        for entry in trace_lines
    )
    assert manifest_seen, "solver never fetched the live manifest"
    assert publish_seen, "solver never submitted the final live publish bundle"


def test_c_bundle_can_be_replayed_through_live_publish() -> None:
    ensure_service()
    bundle = load_json(BUNDLE_PATH)
    response = requests.post(f"{API_URL}/publish", json=bundle, timeout=30)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["accepted"] is True


def test_d_alternate_fixture_builds_and_publishes() -> None:
    alt_root = TESTS_ROOT / "fixtures_alt" / "raw"
    output_root = Path("/tmp/marketplace-alt-output")
    warehouse_path = output_root / "warehouse.duckdb"
    with running_audit_service(alt_root, output_root) as service:
        bundle, receipt = build_and_publish(alt_root, warehouse_path, service["api_url"])
        assert receipt["accepted"] is True
        assert bundle["warehouse_path"] == str(warehouse_path)
        assert len(bundle["tables"]) == 2
        trace_lines = load_jsonl(service["trace_path"])
        assert any(entry.get("event") == "manifest" for entry in trace_lines)
        assert any(entry.get("event") == "publish" for entry in trace_lines)


def test_e_shuffled_input_order_builds_and_publishes(tmp_path: Path) -> None:
    shuffled_root = tmp_path / "raw"
    shuffled_root.mkdir(parents=True, exist_ok=True)
    for name in ["sellers.csv", "catalog.csv", "refunds.csv"]:
        (shuffled_root / name).write_bytes((DATA_ROOT / name).read_bytes())

    orders_lines = (DATA_ROOT / "orders_cdc.jsonl").read_text(encoding="utf-8").splitlines()
    shipment_lines = (DATA_ROOT / "shipment_events.jsonl").read_text(encoding="utf-8").splitlines()
    (shuffled_root / "orders_cdc.jsonl").write_text("\n".join(reversed(orders_lines)) + "\n", encoding="utf-8")
    (shuffled_root / "shipment_events.jsonl").write_text(
        "\n".join(reversed(shipment_lines)) + "\n",
        encoding="utf-8",
    )

    output_root = tmp_path / "shuffle-output"
    warehouse_path = output_root / "warehouse.duckdb"
    with running_audit_service(shuffled_root, output_root) as service:
        _, receipt = build_and_publish(shuffled_root, warehouse_path, service["api_url"])
        assert receipt["accepted"] is True


def test_f_outputs_are_not_placeholder_tables() -> None:
    seller_daily = load_table(WAREHOUSE_PATH, "seller_daily_mart", ["snapshot_date", "seller_id"])
    sku_fulfillment = load_table(WAREHOUSE_PATH, "sku_fulfillment_mart", ["snapshot_date", "seller_id", "sku"])
    assert seller_daily["completed_lines"].sum() > 0
    assert seller_daily["cancelled_lines"].sum() > 0
    assert seller_daily["refunded_revenue_usd"].sum() > 0
    assert seller_daily["net_revenue_usd"].sum() > 0
    assert float(seller_daily["avg_hours_to_ship"].max()) > 0
    assert float(sku_fulfillment["on_time_ship_rate"].max()) == 1.0
    assert float(sku_fulfillment["on_time_ship_rate"].min()) == 0.0
