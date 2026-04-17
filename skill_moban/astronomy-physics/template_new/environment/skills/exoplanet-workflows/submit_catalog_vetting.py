#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

import requests


API_URL = "http://127.0.0.1:8124"
REPORT_PATH = Path("/app/output/catalog_vetting.json")
RECEIPT_PATH = Path("/app/output/catalog_audit_receipt.json")


def canonical_sha256(payload: dict) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def main() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    response = requests.post(f"{API_URL}/audit", json=report, timeout=30)
    payload = response.json()
    response.raise_for_status()

    receipt = {
        "request_sha256": canonical_sha256(report),
        "accepted": bool(payload["accepted"]),
        "snapshot_id": payload["snapshot_id"],
        "status": payload["status"],
        "accepted_targets": int(payload["accepted_targets"]),
    }
    RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
