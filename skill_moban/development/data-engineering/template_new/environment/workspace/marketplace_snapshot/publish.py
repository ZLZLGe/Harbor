from __future__ import annotations

from pathlib import Path

import requests

from .common import API_URL, BUNDLE_PATH, RECEIPT_PATH, WAREHOUSE_PATH, canonical_table_hash, fetch_manifest, write_json


def build_publish_bundle(warehouse_path: Path = WAREHOUSE_PATH, api_url: str = API_URL) -> dict:
    manifest = fetch_manifest(api_url)
    return {
        "snapshot_id": manifest["snapshot_id"],
        "contract_version": manifest["contract_version"],
        "warehouse_path": manifest["warehouse_path"],
        "tables": [
            {
                "name": "seller_daily_mart",
                "row_count": 0,
                "sha256": canonical_table_hash(
                    warehouse_path,
                    "seller_daily_mart",
                    ["snapshot_date", "seller_id"],
                ),
            },
            {
                "name": "sku_fulfillment_mart",
                "row_count": 0,
                "sha256": canonical_table_hash(
                    warehouse_path,
                    "sku_fulfillment_mart",
                    ["snapshot_date", "seller_id", "sku"],
                ),
            },
        ],
    }


def publish_bundle(bundle: dict, api_url: str = API_URL) -> dict:
    response = requests.post(f"{api_url}/publish", json=bundle, timeout=30)
    response.raise_for_status()
    return response.json()


def write_bundle_and_receipt(bundle: dict, receipt: dict) -> None:
    write_json(BUNDLE_PATH, bundle)
    write_json(RECEIPT_PATH, receipt)
