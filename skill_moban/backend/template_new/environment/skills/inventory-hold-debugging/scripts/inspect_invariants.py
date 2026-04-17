#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path

import requests


CHECKOUT_API_URL = os.environ.get("CHECKOUT_API_URL", "http://127.0.0.1:8120")
DB_PATH = Path(os.environ.get("CHECKOUT_DB_PATH", "/app/workspace/state/checkout.db"))


def _load_local_holds() -> list[dict[str, object]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM holds ORDER BY created_at, hold_id").fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def _load_idempotency_records() -> list[dict[str, object]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT idempotency_key, hold_id, request_fingerprint, created_at FROM idempotency_records ORDER BY created_at"
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def _load_ledger_snapshot() -> dict[str, object]:
    response = requests.get(f"{CHECKOUT_API_URL}/internal/state", timeout=10)
    response.raise_for_status()
    return response.json()["ledger"]


def main() -> None:
    local_holds = _load_local_holds()
    idempotency_records = _load_idempotency_records()
    ledger_snapshot = _load_ledger_snapshot()

    local_active = defaultdict(int)
    for hold in local_holds:
        if hold["status"] == "active":
            local_active[(hold["sku"], hold["location"])] += int(hold["quantity"])

    ledger_active = defaultdict(int)
    orphan_leases = []
    for hold in ledger_snapshot["holds"]:
        if hold["state"] == "active":
            ledger_active[(hold["sku"], hold["location"])] += int(hold["quantity"])
            if not any(local["ledger_token"] == hold["ledger_token"] for local in local_holds):
                orphan_leases.append(hold["ledger_token"])

    mismatches = []
    keys = sorted(set(local_active) | set(ledger_active))
    for key in keys:
        if local_active[key] != ledger_active[key]:
            mismatches.append(
                {
                    "sku": key[0],
                    "location": key[1],
                    "local_active_qty": local_active[key],
                    "ledger_active_qty": ledger_active[key],
                }
            )

    missing_local_holds = [
        {
            "idempotency_key": record["idempotency_key"],
            "missing_hold_id": record["hold_id"],
        }
        for record in idempotency_records
        if not any(local["hold_id"] == record["hold_id"] for local in local_holds)
    ]

    print(
        json.dumps(
            {
                "db_path": str(DB_PATH),
                "local_holds": local_holds,
                "idempotency_records": idempotency_records,
                "missing_local_holds": missing_local_holds,
                "orphan_ledger_tokens": orphan_leases,
                "active_quantity_mismatches": mismatches,
                "ledger_events": ledger_snapshot["events"][-10:],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
