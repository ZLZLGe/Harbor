from __future__ import annotations

import time

from conftest import (
    availability,
    cancel_hold,
    confirm_hold,
    delete_local_hold_row,
    get_hold,
    ledger_snapshot,
    local_hold_row,
    post_hold,
)


def _active_holds(snapshot: dict, *, sku: str, location: str) -> list[dict]:
    return [
        hold
        for hold in snapshot["holds"]
        if hold["sku"] == sku and hold["location"] == location and hold["state"] == "active"
    ]


def test_retry_is_idempotent_and_does_not_double_reserve() -> None:
    baseline = availability("CHAIR-RED-001", "store-nyc").json()
    assert baseline["available"] == 18

    first = post_hold(
        sku="CHAIR-RED-001",
        location="store-nyc",
        quantity=2,
        hold_seconds=6,
        customer_id="cust-a",
        key="retry-case-1",
    )
    second = post_hold(
        sku="CHAIR-RED-001",
        location="store-nyc",
        quantity=2,
        hold_seconds=6,
        customer_id="cust-a",
        key="retry-case-1",
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["hold_id"] == second_payload["hold_id"]
    assert second_payload["replayed"] is True

    after = availability("CHAIR-RED-001", "store-nyc")
    assert after.status_code == 200, after.text
    after_payload = after.json()
    assert after_payload["reserved"] == 2
    assert after_payload["available"] == 16

    snapshot = ledger_snapshot()
    active = _active_holds(snapshot, sku="CHAIR-RED-001", location="store-nyc")
    assert len(active) == 1
    assert active[0]["quantity"] == 2


def test_retry_recovers_when_local_hold_row_is_missing() -> None:
    created = post_hold(
        sku="CHAIR-RED-001",
        location="store-nyc",
        quantity=2,
        hold_seconds=6,
        customer_id="cust-recover",
        key="recover-case-1",
    )
    assert created.status_code == 201, created.text
    hold_id = created.json()["hold_id"]

    delete_local_hold_row(hold_id)

    retried = post_hold(
        sku="CHAIR-RED-001",
        location="store-nyc",
        quantity=2,
        hold_seconds=6,
        customer_id="cust-recover",
        key="recover-case-1",
    )
    assert retried.status_code == 200, retried.text
    assert retried.json()["hold_id"] == hold_id

    hold = get_hold(hold_id)
    assert hold.status_code == 200, hold.text
    assert hold.json()["status"] == "active"

    after = availability("CHAIR-RED-001", "store-nyc").json()
    assert after["reserved"] == 2
    assert after["available"] == 16

    snapshot = ledger_snapshot()
    active = _active_holds(snapshot, sku="CHAIR-RED-001", location="store-nyc")
    assert len(active) == 1


def test_expired_hold_releases_inventory() -> None:
    created = post_hold(
        sku="LAMP-BLUE-002",
        location="store-nyc",
        quantity=3,
        hold_seconds=2,
        customer_id="cust-b",
        key="expiry-case-1",
    )
    assert created.status_code == 201, created.text

    time.sleep(3)

    after = availability("LAMP-BLUE-002", "store-nyc")
    assert after.status_code == 200, after.text
    payload = after.json()
    assert payload["reserved"] == 0
    assert payload["available"] == 14

    snapshot = ledger_snapshot()
    active = _active_holds(snapshot, sku="LAMP-BLUE-002", location="store-nyc")
    assert active == []


def test_idle_expiry_converges_local_hold_state_without_followup_requests() -> None:
    created = post_hold(
        sku="LAMP-BLUE-002",
        location="store-nyc",
        quantity=2,
        hold_seconds=2,
        customer_id="cust-idle-expiry",
        key="idle-expiry-case-1",
    )
    assert created.status_code == 201, created.text
    hold_id = created.json()["hold_id"]

    time.sleep(3)

    local_row = local_hold_row(hold_id)
    assert local_row is not None
    assert local_row["status"] == "expired"

    snapshot = ledger_snapshot()
    ledger_hold = next(hold for hold in snapshot["holds"] if hold["ledger_token"] == local_row["ledger_token"])
    assert ledger_hold["state"] == "expired"


def test_confirm_after_expiry_returns_conflict() -> None:
    created = post_hold(
        sku="DESK-OAK-003",
        location="store-nyc",
        quantity=1,
        hold_seconds=2,
        customer_id="cust-c",
        key="confirm-expired-case",
    )
    assert created.status_code == 201, created.text
    hold_id = created.json()["hold_id"]

    time.sleep(3)

    confirmed = confirm_hold(hold_id, "order-expired-1")
    assert confirmed.status_code == 409, confirmed.text

    hold = get_hold(hold_id)
    assert hold.status_code == 200, hold.text
    assert hold.json()["status"] == "expired"

    snapshot = ledger_snapshot()
    commit_events = [event for event in snapshot["events"] if event["event_type"] == "commit"]
    assert commit_events == []


def test_cancel_is_idempotent_and_releases_once() -> None:
    created = post_hold(
        sku="DESK-OAK-003",
        location="store-nyc",
        quantity=1,
        hold_seconds=8,
        customer_id="cust-d",
        key="cancel-case-1",
    )
    hold_id = created.json()["hold_id"]

    first_cancel = cancel_hold(hold_id)
    second_cancel = cancel_hold(hold_id)

    assert first_cancel.status_code == 200, first_cancel.text
    assert second_cancel.status_code == 200, second_cancel.text
    assert first_cancel.json()["status"] == "cancelled"
    assert second_cancel.json()["status"] == "cancelled"

    after = availability("DESK-OAK-003", "store-nyc").json()
    assert after["reserved"] == 0
    assert after["available"] == 6

    snapshot = ledger_snapshot()
    release_events = [event for event in snapshot["events"] if event["event_type"] == "release"]
    assert len(release_events) == 1


def test_mixed_sequence_preserves_location_isolation() -> None:
    nyc_hold = post_hold(
        sku="CHAIR-RED-001",
        location="store-nyc",
        quantity=2,
        hold_seconds=8,
        customer_id="cust-m1",
        key="mixed-nyc-chair",
    )
    sf_hold = post_hold(
        sku="CHAIR-RED-001",
        location="store-sf",
        quantity=1,
        hold_seconds=8,
        customer_id="cust-m2",
        key="mixed-sf-chair",
    )
    lamp_hold = post_hold(
        sku="LAMP-BLUE-002",
        location="store-nyc",
        quantity=3,
        hold_seconds=8,
        customer_id="cust-m3",
        key="mixed-nyc-lamp",
    )

    assert nyc_hold.status_code == 201
    assert sf_hold.status_code == 201
    assert lamp_hold.status_code == 201

    assert confirm_hold(nyc_hold.json()["hold_id"], "order-mixed-1").status_code == 200
    assert cancel_hold(lamp_hold.json()["hold_id"]).status_code == 200

    nyc_chair = availability("CHAIR-RED-001", "store-nyc").json()
    sf_chair = availability("CHAIR-RED-001", "store-sf").json()
    nyc_lamp = availability("LAMP-BLUE-002", "store-nyc").json()

    assert nyc_chair["on_hand"] == 18
    assert nyc_chair["reserved"] == 0
    assert nyc_chair["available"] == 16

    assert sf_chair["on_hand"] == 12
    assert sf_chair["reserved"] == 1
    assert sf_chair["available"] == 10

    assert nyc_lamp["on_hand"] == 15
    assert nyc_lamp["reserved"] == 0
    assert nyc_lamp["available"] == 14
