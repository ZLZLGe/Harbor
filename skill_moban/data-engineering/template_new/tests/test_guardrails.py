from __future__ import annotations

from pathlib import Path

from conftest import DATA_ROOT, SERVICE_BINARY_PATH, SERVICE_PATH, protected_file_sha


EXPECTED_SERVER_SHA_PATH = Path("/opt/audit-service.sha256")


def test_hidden_service_and_protected_inputs_unchanged() -> None:
    assert SERVICE_PATH.exists(), "Missing service bootstrap launcher"
    assert protected_file_sha(SERVICE_BINARY_PATH) == EXPECTED_SERVER_SHA_PATH.read_text(encoding="utf-8").strip()
    protected_inputs = [
        DATA_ROOT / "orders_cdc.jsonl",
        DATA_ROOT / "shipment_events.jsonl",
        DATA_ROOT / "refunds.csv",
        DATA_ROOT / "sellers.csv",
        DATA_ROOT / "catalog.csv",
    ]
    for path in protected_inputs:
        assert path.exists(), f"Missing protected input: {path}"


def test_live_receipt_was_not_handwritten() -> None:
    from conftest import BUNDLE_PATH, LAST_PUBLISH_PATH, RECEIPT_PATH, canonical_json_sha, load_json

    bundle = load_json(BUNDLE_PATH)
    receipt = load_json(RECEIPT_PATH)
    last_publish = load_json(LAST_PUBLISH_PATH)
    request_sha = canonical_json_sha(bundle)
    assert receipt["request_sha256"] == request_sha
    assert last_publish["payload_sha256"] == request_sha
    assert receipt["accepted"] is True
    assert last_publish["accepted"] is True
