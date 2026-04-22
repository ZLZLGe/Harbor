#!/usr/bin/env python3
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


API_BASE = os.environ.get("ACADEMIC_API_URL", "http://127.0.0.1:8123")
SERVICE_CANDIDATES = [
    Path("/services/academic-api/server"),
    Path("/opt/academic-api/server.py"),
    Path("/services/academic-api/server.py"),
]


def _healthcheck() -> bool:
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def ensure_service() -> None:
    if _healthcheck():
        return

    for candidate in SERVICE_CANDIDATES:
        if not candidate.exists():
            continue
        command = [str(candidate)]
        if candidate.suffix == ".py":
            command = [sys.executable, str(candidate)]
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            time.sleep(0.5)
            if _healthcheck():
                return
        break

    raise RuntimeError(
        "Local review validation service is unavailable. "
        "Start the academic API before auditing the workspace."
    )
