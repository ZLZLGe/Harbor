from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import requests


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
PUBLIC_APP_ROOT = WORKSPACE_ROOT / "checkout-api"
LEDGER_SERVER = Path(os.environ.get("LEDGER_SERVER_PATH", "/services/inventory-ledger/server.py"))
CHECKOUT_API_URL = os.environ.get("CHECKOUT_API_URL", "http://127.0.0.1:8120")
LEDGER_API_URL = os.environ.get("LEDGER_API_URL", "http://127.0.0.1:8131")
CHECKOUT_DB_PATH = Path(os.environ.get("CHECKOUT_DB_PATH", "/app/workspace/state/checkout.db"))


def wait_for_health(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=2)
            if response.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}")


def is_healthy(url: str) -> bool:
    try:
        return requests.get(url, timeout=2).ok
    except requests.RequestException:
        return False


@pytest.fixture(scope="session", autouse=True)
def running_services() -> Any:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{PUBLIC_APP_ROOT}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(PUBLIC_APP_ROOT)

    started: list[subprocess.Popen[str]] = []

    if not is_healthy(f"{LEDGER_API_URL}/health"):
        ledger_proc = subprocess.Popen(
            [sys.executable, str(LEDGER_SERVER)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        started.append(ledger_proc)
        wait_for_health(f"{LEDGER_API_URL}/health")

    if not is_healthy(f"{CHECKOUT_API_URL}/health"):
        public_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "checkout_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8120",
                "--app-dir",
                str(PUBLIC_APP_ROOT),
                "--log-level",
                "warning",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        started.append(public_proc)
        wait_for_health(f"{CHECKOUT_API_URL}/health")

    yield

    for proc in reversed(started):
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def reset_stack() -> dict[str, Any]:
    response = requests.post(f"{CHECKOUT_API_URL}/internal/reset", timeout=10)
    response.raise_for_status()
    return response.json()


@pytest.fixture(autouse=True)
def clean_state(running_services: Any) -> None:
    reset_stack()


def post_hold(*, sku: str, location: str, quantity: int, hold_seconds: int, customer_id: str, key: str) -> requests.Response:
    return requests.post(
        f"{CHECKOUT_API_URL}/api/v1/holds",
        headers={"Idempotency-Key": key},
        json={
            "sku": sku,
            "location": location,
            "quantity": quantity,
            "hold_seconds": hold_seconds,
            "customer_id": customer_id,
        },
        timeout=10,
    )


def get_hold(hold_id: str) -> requests.Response:
    return requests.get(f"{CHECKOUT_API_URL}/api/v1/holds/{hold_id}", timeout=10)


def availability(sku: str, location: str) -> requests.Response:
    return requests.get(
        f"{CHECKOUT_API_URL}/api/v1/availability",
        params={"sku": sku, "location": location},
        timeout=10,
    )


def confirm_hold(hold_id: str, order_id: str) -> requests.Response:
    return requests.post(
        f"{CHECKOUT_API_URL}/api/v1/orders/confirm",
        json={"hold_id": hold_id, "order_id": order_id},
        timeout=10,
    )


def cancel_hold(hold_id: str, reason: str = "customer-request") -> requests.Response:
    return requests.post(
        f"{CHECKOUT_API_URL}/api/v1/orders/cancel",
        json={"hold_id": hold_id, "reason": reason},
        timeout=10,
    )


def ledger_snapshot() -> dict[str, Any]:
    response = requests.get(f"{LEDGER_API_URL}/internal/snapshot", timeout=10)
    response.raise_for_status()
    return response.json()


def local_hold_row(hold_id: str) -> dict[str, Any] | None:
    conn = sqlite3.connect(CHECKOUT_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM holds WHERE hold_id = ?", (hold_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row is not None else None


def delete_local_hold_row(hold_id: str) -> None:
    conn = sqlite3.connect(CHECKOUT_DB_PATH)
    try:
        conn.execute("DELETE FROM holds WHERE hold_id = ?", (hold_id,))
        conn.commit()
    finally:
        conn.close()
