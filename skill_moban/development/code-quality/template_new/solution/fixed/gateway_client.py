from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any

import requests


GATEWAY_URL = os.environ.get("SETTLEMENT_GATEWAY_URL", "http://127.0.0.1:8320")
GATEWAY_TOKEN = os.environ.get("SETTLEMENT_GATEWAY_TOKEN", "settlement-gateway-demo-token")


def ensure_gateway_running() -> None:
    try:
        requests.get(f"{GATEWAY_URL}/health", timeout=1).raise_for_status()
        return
    except requests.RequestException:
        pass

    env = os.environ.copy()
    env.setdefault("SETTLEMENT_GATEWAY_TOKEN", GATEWAY_TOKEN)
    subprocess.Popen(
        [sys.executable, "/services/settlement-gateway/server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        start_new_session=True,
    )

    for _ in range(40):
        try:
            requests.get(f"{GATEWAY_URL}/health", timeout=1).raise_for_status()
            return
        except requests.RequestException:
            time.sleep(0.25)

    raise RuntimeError("settlement gateway did not start")


def _get(path: str) -> dict[str, Any]:
    ensure_gateway_running()
    response = requests.get(f"{GATEWAY_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def _post(path: str, *, scenario: str | None = None, rows: list[dict[str, str]] | None = None) -> dict[str, Any]:
    ensure_gateway_running()
    response = requests.post(
        f"{GATEWAY_URL}{path}",
        params={"scenario": scenario} if scenario is not None else None,
        headers={"X-Settlement-Gateway-Token": GATEWAY_TOKEN},
        json={"rows": rows} if rows is not None else None,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def reset_gateway_audit() -> dict[str, Any]:
    return _post("/api/v1/reset")


def gateway_audit() -> dict[str, Any]:
    return _get("/api/v1/audit")


def gateway_integrity() -> dict[str, str]:
    return _get("/api/v1/integrity")


def validate_daily(*, scenario: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    return _post("/api/v1/validate/daily", scenario=scenario, rows=rows)


def validate_monthly(*, scenario: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    return _post("/api/v1/validate/monthly", scenario=scenario, rows=rows)
