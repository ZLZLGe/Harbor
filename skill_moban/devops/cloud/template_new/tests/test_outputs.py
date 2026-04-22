from __future__ import annotations

from conftest import EXPECTED_SNAPSHOT_ID, mirror_audit, public_get, reset_and_apply


def test_apply_produces_healthy_revision() -> None:
    status = reset_and_apply()
    assert status["healthy"] is True, status
    assert status["issues"] == []

    health = public_get("/healthz")
    assert health.status_code == 200, health.text
    assert health.json()["ok"] is True


def test_summary_uses_live_mirror_snapshot_for_eastus2_containerapps() -> None:
    reset_and_apply()

    response = public_get("/api/v1/rollouts/summary?region=eastus2&service=containerapps")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["snapshot_id"] == EXPECTED_SNAPSHOT_ID
    assert payload["incident_count"] == 2
    assert payload["open_incident_count"] == 2
    assert payload["critical_open_count"] == 1
    assert payload["latest_incident_id"] == "AZ-ACA-20260416-002"


def test_summary_counts_for_storage_match_live_snapshot() -> None:
    reset_and_apply()

    response = public_get("/api/v1/rollouts/summary?region=eastus2&service=storage")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["snapshot_id"] == EXPECTED_SNAPSHOT_ID
    assert payload["incident_count"] == 1
    assert payload["open_incident_count"] == 1
    assert payload["critical_open_count"] == 1
    assert payload["latest_incident_id"] == "AZ-STO-20260414-007"


def test_summary_counts_for_servicebus_match_live_snapshot() -> None:
    reset_and_apply()

    response = public_get("/api/v1/rollouts/summary?region=centralus&service=servicebus")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["snapshot_id"] == EXPECTED_SNAPSHOT_ID
    assert payload["incident_count"] == 2
    assert payload["open_incident_count"] == 1
    assert payload["critical_open_count"] == 1
    assert payload["latest_incident_id"] == "AZ-SB-20260413-008"


def test_summary_counts_for_redis_match_live_snapshot() -> None:
    reset_and_apply()

    response = public_get("/api/v1/rollouts/summary?region=northeurope&service=redis")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["snapshot_id"] == EXPECTED_SNAPSHOT_ID
    assert payload["incident_count"] == 1
    assert payload["open_incident_count"] == 1
    assert payload["critical_open_count"] == 0
    assert payload["latest_incident_id"] == "AZ-RDS-20260410-005"


def test_incidents_are_sorted_newest_first() -> None:
    reset_and_apply()

    response = public_get("/api/v1/rollouts/incidents?region=eastus2&service=containerapps")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["snapshot_id"] == EXPECTED_SNAPSHOT_ID
    ids = [item["tracking_id"] for item in payload["items"]]
    assert ids == ["AZ-ACA-20260416-002", "AZ-ACA-20260415-001"]


def test_servicebus_incidents_are_sorted_newest_first() -> None:
    reset_and_apply()

    response = public_get("/api/v1/rollouts/incidents?region=centralus&service=servicebus")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["snapshot_id"] == EXPECTED_SNAPSHOT_ID
    ids = [item["tracking_id"] for item in payload["items"]]
    assert ids == ["AZ-SB-20260413-008", "AZ-SB-20260411-003"]


def test_public_requests_leave_real_mirror_audit_evidence() -> None:
    reset_and_apply()

    summary = public_get("/api/v1/rollouts/summary?region=eastus2&service=containerapps")
    assert summary.status_code == 200, summary.text

    audit = mirror_audit()
    authorized = [event for event in audit["events"] if event["authorized"] is True]
    assert authorized, audit
