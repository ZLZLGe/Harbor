#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import requests


CHECKOUT_API_URL = os.environ.get("CHECKOUT_API_URL", "http://127.0.0.1:8120")


def _request(step: dict[str, object]) -> dict[str, object]:
    method = str(step["method"])
    path = str(step["path"])
    headers = dict(step.get("headers") or {})
    json_body = step.get("json")
    response = requests.request(
        method,
        f"{CHECKOUT_API_URL}{path}",
        headers=headers,
        json=json_body,
        timeout=10,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    return {
        "method": method,
        "path": path,
        "status_code": response.status_code,
        "payload": payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("replay_path", type=Path)
    args = parser.parse_args()

    replay = json.loads(args.replay_path.read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []

    for step in replay["steps"]:
        if "sleep_seconds" in step:
            seconds = float(step["sleep_seconds"])
            time.sleep(seconds)
            results.append({"sleep_seconds": seconds})
            continue
        results.append(_request(step))

    print(json.dumps({"replay": replay["name"], "results": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
