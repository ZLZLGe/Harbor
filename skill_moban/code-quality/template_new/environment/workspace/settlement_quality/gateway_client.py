from __future__ import annotations

import os
from typing import Any

import requests


GATEWAY_URL = os.environ.get("SETTLEMENT_GATEWAY_URL", "http://127.0.0.1:8320")
GATEWAY_TOKEN = os.environ.get("SETTLEMENT_GATEWAY_TOKEN", "settlement-gateway-demo-token")


def _post(path: str, *, scenario: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    response = requests.post(
        f"{GATEWAY_URL}{path}",
        params={"scenario": scenario},
        headers={"X-Settlement-Gateway-Token": GATEWAY_TOKEN},
        json={"rows": rows},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def validate_daily(*, scenario: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    return _post("/api/v1/validate/daily", scenario=scenario, rows=rows)


def validate_monthly(*, scenario: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    return _post("/api/v1/validate/monthly", scenario=scenario, rows=rows)
