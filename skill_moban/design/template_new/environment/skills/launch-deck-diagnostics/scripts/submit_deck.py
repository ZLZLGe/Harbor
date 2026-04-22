#!/usr/bin/env python3
from __future__ import annotations

import json

import requests

from common import QA_URL, RECEIPT_PATH, SUBMISSION_PATH, write_json


def main() -> None:
    payload = json.loads(SUBMISSION_PATH.read_text(encoding="utf-8"))
    response = requests.post(f"{QA_URL}/validate", json=payload, timeout=30)
    response.raise_for_status()
    write_json(RECEIPT_PATH, response.json())
    print(f"Wrote {RECEIPT_PATH}")


if __name__ == "__main__":
    main()
