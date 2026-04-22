from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
STATE_DIR = WORKSPACE_ROOT / "state"
OUT_DIR = WORKSPACE_ROOT / "out"
DATA_DIR = WORKSPACE_ROOT / "data"
BROKER_URL = os.environ.get("RELEASE_BROKER_URL", "http://127.0.0.1:8310")
BROKER_TOKEN = os.environ.get("RELEASE_BROKER_TOKEN", "release-broker-demo-token")


def ensure_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_broker_running() -> None:
    try:
        requests.get(f"{BROKER_URL}/health", timeout=1).raise_for_status()
        return
    except requests.RequestException:
        pass

    subprocess.Popen(
        [sys.executable, "/services/release-broker/server.py"],
        stdout=(WORKSPACE_ROOT / "state" / "release-broker.stdout.log").open("a", encoding="utf-8"),
        stderr=(WORKSPACE_ROOT / "state" / "release-broker.stderr.log").open("a", encoding="utf-8"),
        start_new_session=True,
    )

    for _ in range(40):
        try:
            requests.get(f"{BROKER_URL}/health", timeout=1).raise_for_status()
            return
        except requests.RequestException:
            time.sleep(0.25)

    raise RuntimeError("release broker did not start")


def broker_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_dirs()
    ensure_broker_running()
    response = requests.get(
        f"{BROKER_URL}{path}",
        headers={"X-Release-Broker-Token": BROKER_TOKEN},
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
