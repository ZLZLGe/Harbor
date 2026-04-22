from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import requests


AUDIT_API_URL = os.environ.get("AUDIT_API_URL", "http://127.0.0.1:8321")
SERVER_PATH = Path(os.environ.get("BOARD_AUDIT_SERVER_PATH", "/services/board-audit/server.py"))


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


@pytest.fixture(scope="session", autouse=True)
def running_service() -> Any:
    try:
        if requests.get(f"{AUDIT_API_URL}/health", timeout=2).ok:
            yield
            return
    except requests.RequestException:
        pass

    proc = subprocess.Popen(
        [sys.executable, str(SERVER_PATH)],
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    wait_for_health(f"{AUDIT_API_URL}/health")
    yield
    proc.terminate()
