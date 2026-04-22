from __future__ import annotations

import json
import os

import requests


BASE_URL = os.environ.get("CONTROL_PLANE_URL", "http://127.0.0.1:8300")


def main() -> None:
    status = requests.get(f"{BASE_URL}/__control/status", timeout=10)
    status.raise_for_status()
    events = requests.get(f"{BASE_URL}/__control/events", timeout=10)
    events.raise_for_status()
    print("status:")
    print(json.dumps(status.json(), indent=2))
    print("\nevents:")
    print(json.dumps(events.json(), indent=2))


if __name__ == "__main__":
    main()
