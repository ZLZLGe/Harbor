from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _to_iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ReserveRequest(BaseModel):
    ledger_token: str
    sku: str
    location: str
    quantity: int = Field(ge=1)
    expires_at: str


class ReleaseRequest(BaseModel):
    ledger_token: str


class CommitRequest(BaseModel):
    ledger_token: str
    order_id: str


class LedgerState:
    def __init__(self, seed_path: Path):
        self.seed_path = seed_path
        self.lock = RLock()
        self.reset()

    def reset(self) -> dict[str, Any]:
        payload = json.loads(self.seed_path.read_text(encoding="utf-8"))
        with self.lock:
            self.snapshot_id = payload["snapshot_id"]
            self.inventory = {
                (item["sku"], item["location"]): {
                    "sku": item["sku"],
                    "location": item["location"],
                    "on_hand": int(item["on_hand"]),
                    "safety_stock": int(item["safety_stock"]),
                }
                for item in payload["inventory"]
            }
            self.holds: dict[str, dict[str, Any]] = {}
            self.events: list[dict[str, Any]] = []
            self._event_id = 0
            self._append_event("reset", {"snapshot_id": self.snapshot_id})
            return self.snapshot()

    def _append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_id += 1
        self.events.append(
            {
                "event_id": self._event_id,
                "event_type": event_type,
                "observed_at": _to_iso(_utcnow()),
                **payload,
            }
        )

    def _reconcile_expired_locked(self) -> None:
        now = _utcnow()
        for token, hold in self.holds.items():
            if hold["state"] == "active" and _from_iso(hold["expires_at"]) <= now:
                hold["state"] = "expired"
                hold["updated_at"] = _to_iso(now)
                self._append_event("expired", {"ledger_token": token, "sku": hold["sku"], "location": hold["location"]})

    def _reserved_qty_locked(self, sku: str, location: str) -> int:
        self._reconcile_expired_locked()
        return sum(
            hold["quantity"]
            for hold in self.holds.values()
            if hold["sku"] == sku and hold["location"] == location and hold["state"] == "active"
        )

    def availability(self, sku: str, location: str) -> dict[str, Any]:
        with self.lock:
            record = self.inventory.get((sku, location))
            if record is None:
                raise KeyError(f"unknown sku/location: {sku}/{location}")
            reserved = self._reserved_qty_locked(sku, location)
            available = max(0, record["on_hand"] - record["safety_stock"] - reserved)
            return {
                "snapshot_id": self.snapshot_id,
                "sku": sku,
                "location": location,
                "on_hand": record["on_hand"],
                "safety_stock": record["safety_stock"],
                "reserved": reserved,
                "available": available,
            }

    def reserve(self, request: ReserveRequest) -> dict[str, Any]:
        with self.lock:
            if request.ledger_token in self.holds:
                hold = self.holds[request.ledger_token]
                return {
                    "snapshot_id": self.snapshot_id,
                    "ledger_token": request.ledger_token,
                    "state": hold["state"],
                    "available": self.availability(request.sku, request.location)["available"],
                }

            record = self.inventory.get((request.sku, request.location))
            if record is None:
                raise KeyError(f"unknown sku/location: {request.sku}/{request.location}")
            reserved = self._reserved_qty_locked(request.sku, request.location)
            available = max(0, record["on_hand"] - record["safety_stock"] - reserved)
            if request.quantity > available:
                raise ValueError("insufficient_stock")

            timestamp = _to_iso(_utcnow())
            self.holds[request.ledger_token] = {
                "ledger_token": request.ledger_token,
                "sku": request.sku,
                "location": request.location,
                "quantity": request.quantity,
                "expires_at": request.expires_at,
                "state": "active",
                "order_id": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            self._append_event(
                "reserve",
                {
                    "ledger_token": request.ledger_token,
                    "sku": request.sku,
                    "location": request.location,
                    "quantity": request.quantity,
                    "expires_at": request.expires_at,
                },
            )
            return {
                "snapshot_id": self.snapshot_id,
                "ledger_token": request.ledger_token,
                "state": "active",
                "available": self.availability(request.sku, request.location)["available"],
            }

    def release(self, ledger_token: str) -> dict[str, Any]:
        with self.lock:
            hold = self.holds.get(ledger_token)
            if hold is None:
                raise KeyError("unknown_hold")
            self._reconcile_expired_locked()
            if hold["state"] != "active":
                raise ValueError(hold["state"])
            hold["state"] = "released"
            hold["updated_at"] = _to_iso(_utcnow())
            self._append_event(
                "release",
                {"ledger_token": ledger_token, "sku": hold["sku"], "location": hold["location"], "quantity": hold["quantity"]},
            )
            return {"snapshot_id": self.snapshot_id, "ledger_token": ledger_token, "released": True}

    def commit(self, ledger_token: str, order_id: str) -> dict[str, Any]:
        with self.lock:
            hold = self.holds.get(ledger_token)
            if hold is None:
                raise KeyError("unknown_hold")
            self._reconcile_expired_locked()
            if hold["state"] == "expired":
                raise RuntimeError("lease_expired")
            if hold["state"] != "active":
                raise ValueError(hold["state"])
            record = self.inventory[(hold["sku"], hold["location"])]
            record["on_hand"] -= hold["quantity"]
            hold["state"] = "committed"
            hold["order_id"] = order_id
            hold["updated_at"] = _to_iso(_utcnow())
            self._append_event(
                "commit",
                {
                    "ledger_token": ledger_token,
                    "order_id": order_id,
                    "sku": hold["sku"],
                    "location": hold["location"],
                    "quantity": hold["quantity"],
                },
            )
            return {"snapshot_id": self.snapshot_id, "ledger_token": ledger_token, "committed": True}

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            self._reconcile_expired_locked()
            return {
                "snapshot_id": self.snapshot_id,
                "inventory": [deepcopy(value) for value in self.inventory.values()],
                "holds": [deepcopy(self.holds[key]) for key in sorted(self.holds)],
                "events": deepcopy(self.events),
            }


seed_path = Path(os.environ.get("INVENTORY_LEDGER_SEED", "/app/workspace/data/catalog/ledger_seed.json"))
state = LedgerState(seed_path)
app = FastAPI(title="inventory-ledger", version="1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "snapshot_id": state.snapshot_id}


@app.post("/internal/reset")
def reset() -> dict[str, Any]:
    return state.reset()


@app.get("/internal/snapshot")
def snapshot() -> dict[str, Any]:
    return state.snapshot()


@app.get("/v1/availability")
def availability(
    sku: str = Query(..., min_length=1),
    location: str = Query(..., min_length=1),
) -> dict[str, Any]:
    try:
        return state.availability(sku, location)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/reserve")
def reserve(request: ReserveRequest) -> dict[str, Any]:
    try:
        return state.reserve(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc


@app.post("/v1/release")
def release(request: ReleaseRequest) -> dict[str, Any]:
    try:
        return state.release(request.ledger_token)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc


@app.post("/v1/commit")
def commit(request: CommitRequest) -> dict[str, Any]:
    try:
        return state.commit(request.ledger_token, request.order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error": str(exc)}) from exc


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8131, log_level="warning")
