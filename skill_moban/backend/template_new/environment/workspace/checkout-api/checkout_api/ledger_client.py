from __future__ import annotations

import os
from typing import Any

import requests


LEDGER_API_URL = os.environ.get("LEDGER_API_URL", "http://127.0.0.1:8131")
TIMEOUT_SEC = 5


class LedgerError(RuntimeError):
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None):
        self.status_code = status_code
        self.payload = payload or {}
        super().__init__(self.payload.get("error") or f"ledger error {status_code}")


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = requests.request(method, f"{LEDGER_API_URL}{path}", timeout=TIMEOUT_SEC, **kwargs)
    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = {"error": response.text.strip() or response.reason}
        raise LedgerError(response.status_code, payload)
    if response.content:
        return response.json()
    return {}


def health() -> dict[str, Any]:
    return _request("GET", "/health")


def reset() -> dict[str, Any]:
    return _request("POST", "/internal/reset")


def availability(sku: str, location: str) -> dict[str, Any]:
    return _request("GET", "/v1/availability", params={"sku": sku, "location": location})


def reserve_hold(ledger_token: str, sku: str, location: str, quantity: int, expires_at: str) -> dict[str, Any]:
    return _request(
        "POST",
        "/v1/reserve",
        json={
            "ledger_token": ledger_token,
            "sku": sku,
            "location": location,
            "quantity": quantity,
            "expires_at": expires_at,
        },
    )


def release_hold(ledger_token: str) -> dict[str, Any]:
    return _request("POST", "/v1/release", json={"ledger_token": ledger_token})


def commit_hold(ledger_token: str, order_id: str) -> dict[str, Any]:
    return _request("POST", "/v1/commit", json={"ledger_token": ledger_token, "order_id": order_id})


def snapshot() -> dict[str, Any]:
    return _request("GET", "/internal/snapshot")
