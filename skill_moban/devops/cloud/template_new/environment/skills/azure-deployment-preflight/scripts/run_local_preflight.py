from __future__ import annotations

import json
import os

import requests


BASE_URL = os.environ.get("CONTROL_PLANE_URL", "http://127.0.0.1:8300")


def main() -> None:
    response = requests.get(f"{BASE_URL}/__control/preflight", timeout=10)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
