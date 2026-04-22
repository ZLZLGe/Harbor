#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import time

import requests

from marketplace_snapshot.common import (
    API_URL,
    BUNDLE_PATH,
    RECEIPT_PATH,
    WAREHOUSE_PATH,
    fetch_manifest,
    write_json,
)
from marketplace_snapshot.publish import publish_bundle

import duckdb
import hashlib


SERVICE_PATH = Path("/services/audit-service/server.pyc")


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


def canonical_frame_hash(database_path: Path, table_name: str, order_by: list[str]) -> tuple[int, str]:
    with duckdb.connect(str(database_path), read_only=True) as conn:
        frame = conn.execute(
            f"SELECT * FROM {table_name} ORDER BY {', '.join(order_by)}"
        ).fetchdf()
    csv_text = frame.to_csv(index=False, lineterminator="\n")
    return int(len(frame)), hashlib.sha256(csv_text.encode("utf-8")).hexdigest()


def main() -> None:
    ensure_service(API_URL)
    manifest = fetch_manifest(API_URL)
    bundle = {
        "snapshot_id": manifest["snapshot_id"],
        "contract_version": manifest["contract_version"],
        "warehouse_path": manifest["warehouse_path"],
        "tables": [],
    }
    for name, order_by in [
        ("seller_daily_mart", ["snapshot_date", "seller_id"]),
        ("sku_fulfillment_mart", ["snapshot_date", "seller_id", "sku"]),
    ]:
        row_count, sha256 = canonical_frame_hash(WAREHOUSE_PATH, name, order_by)
        bundle["tables"].append(
            {
                "name": name,
                "row_count": row_count,
                "sha256": sha256,
            }
        )
    receipt = publish_bundle(bundle, API_URL)
    write_json(BUNDLE_PATH, bundle)
    write_json(RECEIPT_PATH, receipt)


if __name__ == "__main__":
    main()
