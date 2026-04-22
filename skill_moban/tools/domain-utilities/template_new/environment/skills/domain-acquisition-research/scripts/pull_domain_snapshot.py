#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


def ensure_service(base_url: str) -> None:
    try:
        response = requests.get(f"{base_url}/health", timeout=2)
        if response.ok:
            return
    except requests.RequestException:
        pass

    server_path = Path(
        os.environ.get("DOMAIN_SNAPSHOT_SERVER_PATH", "/services/domain-audit/server.py")
    )
    if server_path.exists():
        subprocess.Popen(
            [sys.executable, str(server_path)],
            stdout=open("/tmp/domain-skill-snapshot.log", "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.ok:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError("domain snapshot service did not become healthy")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: pull_domain_snapshot.py <domain>")
    domain = sys.argv[1]
    base_url = os.environ.get("DOMAIN_SNAPSHOT_URL", "http://127.0.0.1:8331")
    ensure_service(base_url)
    response = requests.get(f"{base_url}/snapshots/{domain}", timeout=10)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
