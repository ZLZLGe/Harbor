#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import requests


CHECKOUT_API_URL = os.environ.get("CHECKOUT_API_URL", "http://127.0.0.1:8120")


def main() -> None:
    response = requests.post(f"{CHECKOUT_API_URL}/internal/reset", timeout=10)
    response.raise_for_status()
    payload = response.json()
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
