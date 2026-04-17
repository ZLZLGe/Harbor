from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from . import db, ledger_client


class ApiError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _to_iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _fingerprint(payload: dict[str, object]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _public_hold(record: dict[str, object], *, replayed: bool = False) -> dict[str, object]:
    return {
        "hold_id": record["hold_id"],
        "sku": record["sku"],
        "location": record["location"],
        "quantity": record["quantity"],
        "status": record["status"],
        "expires_at": record["expires_at"],
        "idempotency_key": record["idempotency_key"],
        "order_id": record.get("order_id"),
        "replayed": replayed,
    }


def reset_state() -> dict[str, object]:
    db.reset_db()
    ledger = ledger_client.reset()
    return {
        "ok": True,
        "snapshot_id": ledger["snapshot_id"],
        "local_holds": [],
    }


def create_hold(payload: dict[str, object], idempotency_key: str) -> tuple[dict[str, object], int]:
    if not idempotency_key:
        raise ApiError(400, "Idempotency-Key header is required")

    request_fingerprint = _fingerprint(payload)
    now = _now()
    expires_at = _to_iso(now + timedelta(seconds=int(payload["hold_seconds"])))
    ledger_token = f"lease_{uuid4().hex[:16]}"

    # BUG: the ledger reservation is created before checking whether this
    # request was already processed under the same idempotency key.
    ledger_client.reserve_hold(
        ledger_token=ledger_token,
        sku=str(payload["sku"]),
        location=str(payload["location"]),
        quantity=int(payload["quantity"]),
        expires_at=expires_at,
    )

    existing = db.get_idempotency_record(idempotency_key)
    if existing is not None:
        if existing["request_fingerprint"] != request_fingerprint:
            raise ApiError(409, "Idempotency-Key already used with a different payload")
        hold = db.get_hold(str(existing["hold_id"]))
        if hold is None:
            raise ApiError(500, "Idempotency record points to a missing hold")
        return _public_hold(hold, replayed=True), 200

    timestamp = _to_iso(now)
    record = {
        "hold_id": f"hold_{uuid4().hex[:12]}",
        "idempotency_key": idempotency_key,
        "request_fingerprint": request_fingerprint,
        "sku": str(payload["sku"]),
        "location": str(payload["location"]),
        "quantity": int(payload["quantity"]),
        "status": "active",
        "order_id": None,
        "cancel_reason": None,
        "ledger_token": ledger_token,
        "expires_at": expires_at,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    db.insert_hold(record)
    db.insert_idempotency(
        idempotency_key=idempotency_key,
        hold_id=str(record["hold_id"]),
        request_fingerprint=request_fingerprint,
        created_at=timestamp,
    )
    return _public_hold(record), 201


def get_hold(hold_id: str) -> dict[str, object]:
    record = db.get_hold(hold_id)
    if record is None:
        raise ApiError(404, "Hold not found")
    return _public_hold(record)


def availability(sku: str, location: str) -> dict[str, object]:
    ledger_view = ledger_client.availability(sku, location)
    local_reserved = db.sum_active_quantity(sku, location)
    reserved = max(local_reserved, int(ledger_view["reserved"]))
    available = max(0, int(ledger_view["on_hand"]) - int(ledger_view["safety_stock"]) - reserved)
    return {
        "sku": sku,
        "location": location,
        "on_hand": ledger_view["on_hand"],
        "safety_stock": ledger_view["safety_stock"],
        "reserved": reserved,
        "available": available,
        "snapshot_id": ledger_view["snapshot_id"],
    }


def confirm_order(hold_id: str, order_id: str) -> dict[str, object]:
    record = db.get_hold(hold_id)
    if record is None:
        raise ApiError(404, "Hold not found")
    if record["status"] == "cancelled":
        raise ApiError(409, "Cancelled hold cannot be confirmed")
    if record["status"] == "confirmed":
        return _public_hold(record)

    try:
        ledger_client.commit_hold(record["ledger_token"], order_id)
    except ledger_client.LedgerError as exc:
        # BUG: an expired lease from the real ledger should fail confirmation,
        # but the public service currently converts it into a local success.
        if exc.status_code != 409:
            raise ApiError(502, f"Ledger commit failed: {exc.message}") from exc

    db.update_hold_status(record["hold_id"], "confirmed", _to_iso(_now()), order_id=order_id)
    updated = db.get_hold(record["hold_id"])
    return _public_hold(updated)


def cancel_order(hold_id: str, reason: str | None) -> dict[str, object]:
    record = db.get_hold(hold_id)
    if record is None:
        raise ApiError(404, "Hold not found")
    if record["status"] == "confirmed":
        raise ApiError(409, "Confirmed hold cannot be cancelled")
    if record["status"] == "cancelled":
        return _public_hold(record)

    try:
        ledger_client.release_hold(record["ledger_token"])
    except ledger_client.LedgerError as exc:
        if exc.status_code != 409:
            raise ApiError(502, f"Ledger release failed: {exc.message}") from exc

    db.update_hold_status(record["hold_id"], "cancelled", _to_iso(_now()), cancel_reason=reason)
    updated = db.get_hold(record["hold_id"])
    return _public_hold(updated)


def local_state() -> dict[str, object]:
    return {
        "holds": db.list_holds(),
        "ledger": ledger_client.snapshot(),
    }
