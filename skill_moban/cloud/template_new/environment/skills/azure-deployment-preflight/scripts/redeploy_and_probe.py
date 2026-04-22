from __future__ import annotations

import json
import os

import requests


BASE_URL = os.environ.get("CONTROL_PLANE_URL", "http://127.0.0.1:8300")


def main() -> None:
    requests.post(f"{BASE_URL}/__control/reset", timeout=10).raise_for_status()
    apply_response = requests.post(f"{BASE_URL}/__control/apply", timeout=30)
    apply_response.raise_for_status()
    print("apply:")
    print(json.dumps(apply_response.json(), indent=2))

    for path in [
        "/healthz",
        "/api/v1/rollouts/summary?region=eastus2&service=containerapps",
    ]:
        response = requests.get(f"{BASE_URL}{path}", timeout=10)
        print(f"\nGET {path}")
        print(f"status={response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except Exception:  # noqa: BLE001
            print(response.text)


if __name__ == "__main__":
    main()
