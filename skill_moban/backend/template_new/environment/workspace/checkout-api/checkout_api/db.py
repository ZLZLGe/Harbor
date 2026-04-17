from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(os.environ.get("CHECKOUT_DB_PATH", "/app/workspace/state/checkout.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS holds (
    hold_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    sku TEXT NOT NULL,
    location TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT NOT NULL,
    order_id TEXT,
    cancel_reason TEXT,
    ledger_token TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    hold_id TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (hold_id) REFERENCES holds(hold_id)
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def reset_db() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()


def row_to_hold(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "hold_id": row["hold_id"],
        "idempotency_key": row["idempotency_key"],
        "request_fingerprint": row["request_fingerprint"],
        "sku": row["sku"],
        "location": row["location"],
        "quantity": row["quantity"],
        "status": row["status"],
        "order_id": row["order_id"],
        "cancel_reason": row["cancel_reason"],
        "ledger_token": row["ledger_token"],
        "expires_at": row["expires_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def insert_hold(record: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO holds (
                hold_id, idempotency_key, request_fingerprint, sku, location, quantity,
                status, order_id, cancel_reason, ledger_token, expires_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["hold_id"],
                record["idempotency_key"],
                record["request_fingerprint"],
                record["sku"],
                record["location"],
                record["quantity"],
                record["status"],
                record.get("order_id"),
                record.get("cancel_reason"),
                record["ledger_token"],
                record["expires_at"],
                record["created_at"],
                record["updated_at"],
            ),
        )
        conn.commit()


def get_hold(hold_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM holds WHERE hold_id = ?", (hold_id,)).fetchone()
    return row_to_hold(row)


def get_hold_by_idempotency(idempotency_key: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT h.*
            FROM holds h
            JOIN idempotency_records i ON i.hold_id = h.hold_id
            WHERE i.idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
    return row_to_hold(row)


def get_idempotency_record(idempotency_key: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM idempotency_records WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def insert_idempotency(idempotency_key: str, hold_id: str, request_fingerprint: str, created_at: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO idempotency_records (idempotency_key, hold_id, request_fingerprint, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (idempotency_key, hold_id, request_fingerprint, created_at),
        )
        conn.commit()


def sum_active_quantity(sku: str, location: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(quantity), 0) AS total
            FROM holds
            WHERE sku = ? AND location = ? AND status = 'active'
            """,
            (sku, location),
        ).fetchone()
    return int(row["total"]) if row else 0


def expire_holds(now_iso: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE holds
            SET status = 'expired', updated_at = ?
            WHERE status = 'active' AND expires_at <= ?
            """,
            (now_iso, now_iso),
        )
        conn.commit()
    return int(cursor.rowcount)


def update_hold_status(
    hold_id: str,
    status: str,
    updated_at: str,
    *,
    order_id: str | None = None,
    cancel_reason: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE holds
            SET status = ?,
                updated_at = ?,
                order_id = COALESCE(?, order_id),
                cancel_reason = COALESCE(?, cancel_reason)
            WHERE hold_id = ?
            """,
            (status, updated_at, order_id, cancel_reason, hold_id),
        )
        conn.commit()


def list_holds() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM holds ORDER BY created_at, hold_id").fetchall()
    return [row_to_hold(row) for row in rows]
