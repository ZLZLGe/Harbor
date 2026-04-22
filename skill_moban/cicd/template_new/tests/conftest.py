from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests


WORKSPACE_ROOT = Path("/app/workspace")
OUT_DIR = WORKSPACE_ROOT / "out"
STATE_DIR = WORKSPACE_ROOT / "state"
BROKER_URL = "http://127.0.0.1:8310"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_broker_running() -> None:
    try:
        requests.get(f"{BROKER_URL}/health", timeout=1).raise_for_status()
        return
    except requests.RequestException:
        pass

    env = os.environ.copy()
    env.setdefault("RELEASE_BROKER_TOKEN", "release-broker-demo-token")
    subprocess.Popen(
        [sys.executable, "/services/release-broker/server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        start_new_session=True,
    )

    for _ in range(40):
        try:
            requests.get(f"{BROKER_URL}/health", timeout=1).raise_for_status()
            return
        except requests.RequestException:
            time.sleep(0.25)

    raise RuntimeError("release broker did not start")


def broker_get(path: str, params: dict[str, Any] | None = None) -> requests.Response:
    ensure_broker_running()
    return requests.get(f"{BROKER_URL}{path}", params=params, timeout=10)


def broker_post(path: str) -> requests.Response:
    ensure_broker_running()
    return requests.post(f"{BROKER_URL}{path}", timeout=10)


def broker_audit() -> dict[str, Any]:
    response = broker_get("/api/v1/audit")
    response.raise_for_status()
    return response.json()


def broker_integrity() -> dict[str, str]:
    response = broker_get("/api/v1/integrity")
    response.raise_for_status()
    return response.json()


def clean_workspace() -> None:
    for root in (OUT_DIR, STATE_DIR):
        if not root.exists():
            continue
        for path in root.iterdir():
            if path.is_file():
                path.unlink()


def run_release_dry_run() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "-C", str(WORKSPACE_ROOT), "release-dry-run"],
        text=True,
        capture_output=True,
        check=False,
    )


def reset_and_run() -> subprocess.CompletedProcess[str]:
    clean_workspace()
    reset = broker_post("/api/v1/reset")
    reset.raise_for_status()
    return run_release_dry_run()
