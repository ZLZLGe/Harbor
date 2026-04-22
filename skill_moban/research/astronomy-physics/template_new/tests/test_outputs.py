import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import requests


OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/app/output/catalog_vetting.json"))
RECEIPT_PATH = Path(
    os.environ.get("RECEIPT_PATH", "/app/output/catalog_audit_receipt.json")
)
CATALOG_PATH = Path(os.environ.get("CATALOG_PATH", "/app/data/target_catalog.json"))
TRACE_PATH = Path(os.environ.get("TRACE_PATH", "/tmp/observatory_api_trace.jsonl"))
LAST_AUDIT_PATH = Path(
    os.environ.get("LAST_AUDIT_PATH", "/tmp/observatory_last_audit.json")
)
API_URL = os.environ.get("OBSERVATORY_API_URL", "http://127.0.0.1:8124")
TOTAL_CADENCES = 16200
ENTRY_REQUIRED_KEYS = {
    "target_id",
    "rotation_alias_days",
    "transit_period_days",
    "transit_epoch_mjd",
    "duration_hours",
    "depth_ppm",
    "transit_snr",
    "transit_count",
    "odd_even_depth_ratio",
    "secondary_eclipse_snr",
    "quality_points_used",
    "quality_points_removed",
    "quarantine_points_removed",
    "verdict",
    "verdict_reason",
}
RECEIPT_REQUIRED_KEYS = {
    "request_sha256",
    "accepted",
    "snapshot_id",
    "status",
    "accepted_targets",
}


def _ensure_service() -> None:
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            return
    except requests.RequestException:
        pass

    proc = subprocess.Popen(
        ["python3", "/services/observatory-api/server.py"],
        stdout=open("/tmp/observatory-api.log", "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(40):
        try:
            response = requests.get(f"{API_URL}/health", timeout=5)
            if response.status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
    proc.terminate()
    raise AssertionError("observatory API did not start during verifier replay")


def _load_report() -> dict:
    assert OUTPUT_PATH.exists(), "Missing /app/output/catalog_vetting.json"
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "Catalog bundle must be a JSON object"
    return payload


def _load_receipt() -> dict:
    assert RECEIPT_PATH.exists(), "Missing /app/output/catalog_audit_receipt.json"
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "Receipt must be a JSON object"
    return payload


def _load_catalog() -> dict:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_trace() -> list[dict]:
    assert TRACE_PATH.exists(), "Observatory trace file was not created"
    records = []
    for line in TRACE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _load_last_audit() -> dict:
    assert LAST_AUDIT_PATH.exists(), "Missing /tmp/observatory_last_audit.json"
    payload = json.loads(LAST_AUDIT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "Last audit payload must be a JSON object"
    return payload


def test_a_bundle_shape_and_accounting():
    report = _load_report()
    receipt = _load_receipt()
    catalog = _load_catalog()
    assert set(report.keys()) >= {"snapshot_id", "entries"}
    assert RECEIPT_REQUIRED_KEYS.issubset(receipt.keys())
    assert report["snapshot_id"] == catalog["snapshot_id"]
    assert receipt["snapshot_id"] == catalog["snapshot_id"]
    assert receipt["accepted"] is True
    assert receipt["status"] == "accepted"
    assert isinstance(report["entries"], list)
    assert len(report["entries"]) == len(catalog["targets"])
    assert receipt["accepted_targets"] == len(catalog["targets"])

    seen_ids = []
    for entry in report["entries"]:
        assert ENTRY_REQUIRED_KEYS.issubset(entry.keys())
        seen_ids.append(entry["target_id"])
        assert (
            entry["quality_points_used"]
            + entry["quality_points_removed"]
            + entry["quarantine_points_removed"]
            == TOTAL_CADENCES
        )
        assert entry["transit_count"] >= 2
        assert entry["duration_hours"] > 0
        assert entry["depth_ppm"] > 0
        assert isinstance(entry["verdict_reason"], str)
        assert len(entry["verdict_reason"].strip()) >= 40

    expected_ids = [target["target_id"] for target in catalog["targets"]]
    assert sorted(seen_ids) == sorted(expected_ids)
    assert len(seen_ids) == len(set(seen_ids))


def test_b_solver_used_live_catalog_manifest_and_audit_chain():
    report = _load_report()
    receipt = _load_receipt()
    last_audit = _load_last_audit()
    canonical_report = json.dumps(
        report,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    report_hash = hashlib.sha256(canonical_report).hexdigest()

    assert receipt["request_sha256"] == report_hash
    assert last_audit["payload_sha256"] == report_hash
    assert last_audit["accepted"] is True

    trace = _load_trace()
    catalog_seen = any(record.get("event") == "catalog" for record in trace)
    manifest_ids = {
        record.get("target_id")
        for record in trace
        if record.get("event") == "manifest"
    }
    audit_hashes = {
        record.get("payload_sha256")
        for record in trace
        if record.get("event") == "audit"
    }
    expected_ids = {
        target["target_id"] for target in _load_catalog()["targets"]
    }

    assert catalog_seen, "Solver never fetched the live catalog endpoint"
    assert expected_ids.issubset(manifest_ids), "Solver did not fetch every required manifest"
    assert report_hash in audit_hashes, "Solver never submitted the final bundle through the live audit chain"


def test_c_current_bundle_still_passes_live_audit():
    _ensure_service()
    report = _load_report()
    response = requests.post(f"{API_URL}/audit", json=report, timeout=30)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["accepted"] is True
