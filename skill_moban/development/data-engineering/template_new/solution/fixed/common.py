from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import duckdb
import requests


API_URL = "http://127.0.0.1:8331"
OUTPUT_ROOT = Path("/app/output")
WAREHOUSE_PATH = OUTPUT_ROOT / "warehouse.duckdb"
BUNDLE_PATH = OUTPUT_ROOT / "publish_bundle.json"
RECEIPT_PATH = OUTPUT_ROOT / "publish_receipt.json"


def parse_timestamp_utc(value: object) -> datetime:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def canonical_json_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_table_hash(database_path: Path, table_name: str, order_by: Iterable[str]) -> tuple[int, str]:
    order_clause = ", ".join(order_by)
    with duckdb.connect(str(database_path), read_only=True) as conn:
        frame = conn.execute(
            f"SELECT * FROM {table_name} ORDER BY {order_clause}"
        ).fetchdf()
    csv_text = frame.to_csv(index=False, lineterminator="\n")
    return int(len(frame)), hashlib.sha256(csv_text.encode("utf-8")).hexdigest()


def fetch_manifest(api_url: str = API_URL) -> dict:
    response = requests.get(f"{api_url}/manifest", timeout=30)
    response.raise_for_status()
    return response.json()


def ensure_output_root(output_root: Path = OUTPUT_ROOT) -> None:
    output_root.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
