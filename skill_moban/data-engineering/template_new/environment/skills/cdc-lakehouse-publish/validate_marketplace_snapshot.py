#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import duckdb

from marketplace_snapshot.pipeline import build_warehouse
from marketplace_snapshot.publish import build_publish_bundle, publish_bundle


MAIN_ROOT = Path("/app/workspace/data/raw")
ALT_ROOT = Path("/tests/fixtures_alt/raw")
MAIN_WAREHOUSE = Path("/tmp/marketplace-skill-main.duckdb")
SYNTHETIC_WAREHOUSE = Path("/tmp/marketplace-skill-synthetic.duckdb")
API_URL = "http://127.0.0.1:8331"
SERVICE_PATH = Path("/services/audit-service/server.pyc")


def _load_table(path: Path, table_name: str, order_by: list[str]):
    with duckdb.connect(str(path), read_only=True) as conn:
        return conn.execute(
            f"SELECT * FROM {table_name} ORDER BY {', '.join(order_by)}"
        ).fetchdf()


def _frame_hash(frame) -> str:
    csv_text = frame.to_csv(index=False, lineterminator="\n")
    import hashlib

    return hashlib.sha256(csv_text.encode("utf-8")).hexdigest()


def _compare_frames(actual, expected, key_cols: list[str]) -> dict:
    actual_keys = {tuple(row) for row in actual[key_cols].itertuples(index=False, name=None)}
    expected_keys = {tuple(row) for row in expected[key_cols].itertuples(index=False, name=None)}
    return {
        "matches": actual.equals(expected),
        "actual_rows": int(len(actual)),
        "expected_rows": int(len(expected)),
        "actual_sha256": _frame_hash(actual),
        "expected_sha256": _frame_hash(expected),
        "missing_keys_sample": [list(key) for key in sorted(expected_keys - actual_keys)[:5]],
        "extra_keys_sample": [list(key) for key in sorted(actual_keys - expected_keys)[:5]],
    }


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


@contextmanager
def _running_audit_service(data_root: Path, output_root: Path):
    port = _pick_free_port()
    trace_path = output_root / "audit-trace.jsonl"
    publish_path = output_root / "last-publish.json"
    log_path = output_root / "audit-service.log"
    output_root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "MARKETPLACE_DATA_ROOT": str(data_root),
            "MARKETPLACE_OUTPUT_ROOT": str(output_root),
            "MARKETPLACE_AUDIT_TRACE_PATH": str(trace_path),
            "MARKETPLACE_LAST_PUBLISH_PATH": str(publish_path),
            "MARKETPLACE_AUDIT_PORT": str(port),
        }
    )
    proc = subprocess.Popen(
        ["python3", str(SERVICE_PATH)],
        env=env,
        stdout=open(log_path, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    api_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            try:
                import requests

                response = requests.get(f"{api_url}/health", timeout=5)
                if response.status_code == 200:
                    yield api_url
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.25)
        else:
            raise RuntimeError(f"temporary audit service did not start; see {log_path}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _build_synthetic_edge_fixture(root: Path) -> Path:
    raw_root = root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)

    _write_jsonl(
        raw_root / "orders_cdc.jsonl",
        [
            {
                "order_id": "edge-2005",
                "line_id": 1,
                "event_seq": 1,
                "seller_id": "seller-edge",
                "sku": "sku-edge",
                "quantity": 1,
                "order_status": "completed",
                "ordered_at": "2026-03-10T08:00:00-05:00",
                "updated_at": "2026-03-10T08:05:00-05:00",
                "ingested_at": "2026-03-10T13:06:00Z",
                "gross_total_usd": "19.99",
                "gross_total_cents": "",
            },
            {
                "order_id": "edge-2005",
                "line_id": 1,
                "event_seq": 2,
                "seller_id": "seller-edge",
                "sku": "sku-edge",
                "quantity": 1,
                "order_status": "completed",
                "ordered_at": "2026-03-10T08:00:00-05:00",
                "updated_at": "2026-03-10T08:30:00-05:00",
                "ingested_at": "2026-03-10T13:40:00Z",
                "gross_total_usd": "19.99",
                "gross_total_cents": "1799",
            },
            {
                "order_id": "edge-2005",
                "line_id": 1,
                "event_seq": 2,
                "seller_id": "seller-edge",
                "sku": "sku-edge",
                "quantity": 1,
                "order_status": "cancelled",
                "ordered_at": "2026-03-10T08:00:00-05:00",
                "updated_at": "2026-03-10T09:10:00-05:00",
                "ingested_at": "2026-03-10T13:20:00Z",
                "gross_total_usd": "19.99",
                "gross_total_cents": "",
            },
        ],
    )
    _write_jsonl(
        raw_root / "shipment_events.jsonl",
        [
            {
                "order_id": "edge-2005",
                "line_id": 1,
                "event_type": "shipped",
                "event_ts": "2026-03-10T14:30:00Z",
            },
            {
                "order_id": "edge-2005",
                "line_id": 1,
                "event_type": "delivered",
                "event_ts": "2026-03-10T18:00:00Z",
            },
        ],
    )
    (raw_root / "refunds.csv").write_text(
        "refund_id,order_id,line_id,refunded_usd\n"
        "refund-edge-1,edge-2005,1,2.50\n",
        encoding="utf-8",
    )
    (raw_root / "sellers.csv").write_text(
        "seller_id,seller_name,sla_hours\n"
        "seller-edge,Edge Seller,2\n",
        encoding="utf-8",
    )
    (raw_root / "catalog.csv").write_text(
        "sku,category\n"
        "sku-edge,edge-category\n",
        encoding="utf-8",
    )
    return raw_root


def _check_dataset(data_root: Path, warehouse_path: Path, api_url: str) -> dict:
    from probe_marketplace_snapshot import _reference_tables

    if warehouse_path.exists():
        warehouse_path.unlink()
    build_warehouse(data_root=data_root, warehouse_path=warehouse_path)
    seller_daily = _load_table(warehouse_path, "seller_daily_mart", ["snapshot_date", "seller_id"])
    sku_fulfillment = _load_table(warehouse_path, "sku_fulfillment_mart", ["snapshot_date", "seller_id", "sku"])
    expected_daily, expected_sku = _reference_tables(data_root)
    bundle = build_publish_bundle(warehouse_path=warehouse_path, api_url=api_url)
    receipt = None
    publish_error = None
    try:
        receipt = publish_bundle(bundle, api_url=api_url)
    except Exception as exc:  # noqa: BLE001
        publish_error = str(exc)
    return {
        "accepted": bool(receipt["accepted"]) if receipt else False,
        "snapshot_id": receipt["snapshot_id"] if receipt else bundle["snapshot_id"],
        "seller_daily_rows": int(len(seller_daily)),
        "sku_fulfillment_rows": int(len(sku_fulfillment)),
        "bundle_tables": bundle["tables"],
        "publish_error": publish_error,
        "seller_daily_mart": _compare_frames(actual=seller_daily, expected=expected_daily, key_cols=["snapshot_date", "seller_id"]),
        "sku_fulfillment_mart": _compare_frames(
            actual=sku_fulfillment,
            expected=expected_sku,
            key_cols=["snapshot_date", "seller_id", "sku"],
        ),
    }


def main() -> None:
    from submit_marketplace_bundle import ensure_service

    ensure_service(API_URL)
    summary = {
        "main": _check_dataset(MAIN_ROOT, MAIN_WAREHOUSE, API_URL),
    }
    with tempfile.TemporaryDirectory(prefix="marketplace-skill-synthetic-") as tmp_dir:
        synthetic_root = _build_synthetic_edge_fixture(Path(tmp_dir))
        synthetic_output_root = Path(tmp_dir) / "output"
        with _running_audit_service(synthetic_root, synthetic_output_root) as api_url:
            summary["synthetic_edge"] = _check_dataset(
                synthetic_root,
                SYNTHETIC_WAREHOUSE,
                api_url,
            )
    if ALT_ROOT.exists():
        with tempfile.TemporaryDirectory(prefix="marketplace-skill-alt-") as tmp_dir:
            alt_output_root = Path(tmp_dir) / "output"
            with _running_audit_service(ALT_ROOT, alt_output_root) as api_url:
                summary["alt"] = _check_dataset(
                    ALT_ROOT,
                    Path(tmp_dir) / "warehouse.duckdb",
                    api_url,
                )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
