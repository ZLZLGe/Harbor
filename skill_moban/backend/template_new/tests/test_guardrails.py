from __future__ import annotations

import hashlib
import os
from pathlib import Path

from conftest import LEDGER_API_URL, availability, ledger_snapshot, post_hold


EXPECTED_LEDGER_SERVER_SHA256 = "e4e983809e2a4cdd3c2a0c2c7979a4488479a4d13ea94405f6a1815757e66142"
EXPECTED_LEDGER_SEED_SHA256 = "f99ac8b719524287e82f6e462381e6a98d6b021c6410e7564ff022fa901247b8"
LEDGER_SERVER_PATH = Path(os.environ.get("LEDGER_SERVER_PATH", "/services/inventory-ledger/server.py"))
LEDGER_SEED_PATH = Path(os.environ.get("INVENTORY_LEDGER_SEED", "/app/workspace/data/catalog/ledger_seed.json"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hidden_ledger_and_seed_data_unchanged() -> None:
    assert _sha256(LEDGER_SERVER_PATH) == EXPECTED_LEDGER_SERVER_SHA256
    assert _sha256(LEDGER_SEED_PATH) == EXPECTED_LEDGER_SEED_SHA256


def test_public_api_still_drives_real_ledger_events() -> None:
    before = ledger_snapshot()
    before_event_count = len(before["events"])

    created = post_hold(
        sku="CHAIR-RED-001",
        location="store-sf",
        quantity=1,
        hold_seconds=6,
        customer_id="cust-guard",
        key="guard-ledger-chain",
    )
    assert created.status_code == 201, created.text

    after = ledger_snapshot()
    reserve_events = [event for event in after["events"] if event["event_type"] == "reserve"]
    assert len(after["events"]) > before_event_count
    assert reserve_events, "expected at least one reserve event in the downstream ledger"

    public_availability = availability("CHAIR-RED-001", "store-sf").json()
    assert public_availability["snapshot_id"] == after["snapshot_id"]
