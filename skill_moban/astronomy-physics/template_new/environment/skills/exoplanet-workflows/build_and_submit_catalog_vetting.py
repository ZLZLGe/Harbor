#!/usr/bin/env python3
import json
from pathlib import Path

import requests

from probe_catalog_vetting import API_URL, analyze_target
from submit_catalog_vetting import canonical_sha256


REPORT_PATH = Path("/app/output/catalog_vetting.json")
RECEIPT_PATH = Path("/app/output/catalog_audit_receipt.json")


def main() -> None:
    catalog = requests.get(f"{API_URL}/catalog", timeout=20).json()
    entries = []

    for target in catalog["targets"]:
        manifest = requests.get(
            f"{API_URL}/manifest/{target['target_id']}",
            timeout=20,
        ).json()
        entry, _ = analyze_target(target["target_id"], manifest)
        entries.append(entry)

    report = {
        "snapshot_id": catalog["snapshot_id"],
        "entries": entries,
    }
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )

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

    print(
        json.dumps(
            {
                "snapshot_id": catalog["snapshot_id"],
                "target_count": len(entries),
                "receipt_status": receipt["status"],
                "request_sha256": receipt["request_sha256"],
            },
            indent=2,
            ensure_ascii=True,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
