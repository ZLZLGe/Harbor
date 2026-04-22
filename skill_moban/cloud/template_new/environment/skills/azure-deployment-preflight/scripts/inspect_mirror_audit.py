from __future__ import annotations

import json
import os

import requests


BASE_URL = os.environ.get("CONTROL_PLANE_URL", "http://127.0.0.1:8300")


def main() -> None:
    response = requests.get(f"{BASE_URL}/__control/mirror-audit", timeout=10)
    response.raise_for_status()
    payload = response.json()
    print(json.dumps(payload, indent=2))

    authorized = [event for event in payload["events"] if event.get("authorized") is True]
    if not authorized:
        raise SystemExit("mirror audit did not record any authorized downstream requests")


if __name__ == "__main__":
    main()
