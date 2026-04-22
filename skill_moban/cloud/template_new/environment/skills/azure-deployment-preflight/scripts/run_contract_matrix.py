from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = os.environ.get("CONTROL_PLANE_URL", "http://127.0.0.1:8300")
MATRIX_PATH = Path(
    os.environ.get(
        "CONTRACT_MATRIX_PATH",
        "/logs/agent/skills/azure-deployment-preflight/data/contract_matrix.json",
    )
)


def _parse_opened_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _get_json(path: str) -> dict:
    response = requests.get(f"{BASE_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def main() -> None:
    failures: list[str] = []
    queries = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    for entry in queries:
        region = entry["region"]
        service = entry["service"]
        expected_summary = entry["expected_summary"]
        summary = _get_json(f"/api/v1/rollouts/summary?region={region}&service={service}")
        incidents = _get_json(f"/api/v1/rollouts/incidents?region={region}&service={service}")
        items = incidents["items"]
        sorted_copy = sorted(items, key=lambda item: _parse_opened_at(item["opened_at"]), reverse=True)

        print(f"\n== {region}/{service} ==")
        print("summary:")
        print(json.dumps(summary, indent=2))
        print("incidents:")
        print(json.dumps(incidents, indent=2))

        if summary["snapshot_id"] != incidents["snapshot_id"]:
            failures.append(f"{region}/{service}: snapshot_id mismatch between summary and incidents")
        if summary["incident_count"] != expected_summary["incident_count"]:
            failures.append(f"{region}/{service}: incident_count did not match the contract matrix")
        if summary["open_incident_count"] != expected_summary["open_incident_count"]:
            failures.append(f"{region}/{service}: open_incident_count did not match the contract matrix")
        if summary["critical_open_count"] != expected_summary["critical_open_count"]:
            failures.append(f"{region}/{service}: critical_open_count did not match the contract matrix")
        if summary["latest_incident_id"] != expected_summary["latest_incident_id"]:
            failures.append(f"{region}/{service}: latest_incident_id did not match the contract matrix")
        if items != sorted_copy:
            failures.append(f"{region}/{service}: incidents are not sorted newest-first")

    if failures:
        print("\ncontract failures:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("\ncontract matrix passed")


if __name__ == "__main__":
    main()
