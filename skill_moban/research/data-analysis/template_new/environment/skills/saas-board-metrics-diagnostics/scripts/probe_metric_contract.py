#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import requests


CONTRACT_PATH = Path(os.environ.get("BOARD_CONTRACT_PATH", "/app/data/reference/metric_contract.json"))
API_URL = os.environ.get("AUDIT_API_URL", "http://127.0.0.1:8321")


def main() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    manifest = requests.get(f"{API_URL}/manifest", timeout=10).json()

    print("MANIFEST")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print()
    print("METRIC CONTRACT")
    print(f"analysis_window: {contract['analysis_window']}")
    print(f"dimensions: {contract['dimensions']}")
    print("required_metrics:")
    for metric in contract["required_metrics"]:
        print(f"  - {metric['name']}: {metric['description']}")


if __name__ == "__main__":
    main()
