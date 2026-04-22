from __future__ import annotations

from conftest import EXPECTED_SNAPSHOT_ID, control_get, mirror_audit, public_get, reset_and_apply

EXPECTED_CONTROL_PLANE_SHA256 = "9e1cd70921b802309a3e27c2d31302bbe267fe4968c8763b90645f5ada011a15"
EXPECTED_MIRROR_SERVER_SHA256 = "4198509a9810ebd1466467a22155668ee8260c7188f3f85dd052d38fec30ed1d"
EXPECTED_MIRROR_DATA_SHA256 = "502704dfc11bb66d14abcc5a0eb62ec371ea0c9d7b5a33308c0dbd3df23599b1"


def test_hidden_services_and_frozen_data_unchanged() -> None:
    payload = control_get("/__control/integrity").json()
    assert payload["control_plane_sha256"] == EXPECTED_CONTROL_PLANE_SHA256
    assert payload["mirror_server_sha256"] == EXPECTED_MIRROR_SERVER_SHA256
    assert payload["mirror_data_sha256"] == EXPECTED_MIRROR_DATA_SHA256


def test_public_api_does_not_fall_back_to_stale_snapshot() -> None:
    reset_and_apply()

    response = public_get("/api/v1/rollouts/summary?region=eastus2&service=containerapps")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["snapshot_id"] == EXPECTED_SNAPSHOT_ID

    audit = mirror_audit()
    assert any(event["authorized"] is True for event in audit["events"]), audit
