import re
import time

import httpx


APP_BASE = "http://localhost:3000"
SIM_BASE = "http://localhost:3001"


def reset_stats() -> None:
    response = httpx.post(f"{SIM_BASE}/_diagnostics/reset", timeout=10.0)
    assert response.status_code == 200


def read_stats() -> dict[str, int]:
    response = httpx.get(f"{SIM_BASE}/_diagnostics/stats", timeout=10.0)
    assert response.status_code == 200
    payload = response.json()
    return payload["counters"]


def get_simulator_session(client: httpx.Client) -> dict[str, str]:
    response = client.get(f"{SIM_BASE}/api/session")
    assert response.status_code == 200
    return response.json()


def get_simulator_json(client: httpx.Client, path: str, token: str) -> dict | list:
    response = client.get(
        f"{SIM_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()


def extract_block(html: str, tag: str, testid: str) -> str:
    match = re.search(
        rf"<{tag}[^>]*data-testid=\"{re.escape(testid)}\"[^>]*>(.*?)</{tag}>",
        html,
        re.DOTALL,
    )
    assert match, f"missing {testid}"
    return match.group(1)


def strip_tags(fragment: str) -> str:
    return re.sub(r"<[^>]+>", "", fragment)


class TestControlRoomPage:
    def test_control_room_page_meets_budget_and_preserves_panels(self):
        with httpx.Client(timeout=30.0) as client:
            operator = get_simulator_session(client)
            incident_feed = get_simulator_json(client, "/api/incidents", operator["token"])
            service_health = get_simulator_json(client, "/api/service-health", operator["token"])
            deployment_lane = get_simulator_json(client, "/api/deployments", operator["token"])
            approvals = get_simulator_json(client, "/api/approvals", operator["token"])

            warmup = client.get(f"{APP_BASE}/control-room")
            assert warmup.status_code == 200

            reset_stats()
            start = time.time()
            response = client.get(f"{APP_BASE}/control-room")
            elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 1050, f"/control-room took {elapsed_ms:.0f}ms, expected <1050ms"
        assert elapsed_ms > 650, f"/control-room was unrealistically fast at {elapsed_ms:.0f}ms"

        html = response.text
        operator_chip = strip_tags(extract_block(html, "div", "operator-chip"))
        assert operator["displayName"] in operator_chip
        assert operator["region"] in operator_chip

        incident_section = extract_block(html, "section", "incident-feed")
        assert "<li" in incident_section
        assert incident_feed[0]["title"] in incident_section

        service_section = extract_block(html, "section", "service-health")
        assert "<li" in service_section
        assert service_health[0]["service"] in service_section

        deployment_section = extract_block(html, "section", "deployment-lane")
        assert "<li" in deployment_section
        assert deployment_lane[0]["train"] in deployment_section

        approval_section = extract_block(html, "section", "approval-queue")
        assert "<li" in approval_section
        assert approvals[0]["eventId"] in approval_section

        stats = read_stats()
        assert stats["session"] == 1, f"expected 1 session call, saw {stats['session']}"
        assert stats["incidents"] == 1, f"expected 1 incidents call, saw {stats['incidents']}"
        assert stats["serviceHealth"] == 1, f"expected 1 serviceHealth call, saw {stats['serviceHealth']}"
        assert stats["deployments"] == 1, f"expected 1 deployments call, saw {stats['deployments']}"
        assert stats["approvals"] == 1, f"expected 1 approvals call, saw {stats['approvals']}"


class TestEventConfirmationRoute:
    def test_confirm_route_meets_budget_and_keeps_contract(self):
        with httpx.Client(timeout=30.0) as client:
            operator = get_simulator_session(client)
            policy = get_simulator_json(client, "/api/policy/evt-204", operator["token"])

            warmup = client.post(f"{APP_BASE}/api/events/evt-204/confirm")
            assert warmup.status_code == 200

            reset_stats()
            start = time.time()
            response = client.post(f"{APP_BASE}/api/events/evt-204/confirm")
            elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 1100, f"confirm route took {elapsed_ms:.0f}ms, expected <1100ms"
        assert elapsed_ms > 650, f"confirm route was unrealistically fast at {elapsed_ms:.0f}ms"

        payload = response.json()
        assert payload["eventId"] == "evt-204"
        assert payload["status"] == "confirmed"
        assert payload["confirmedBy"] == operator["displayName"]
        assert payload["runbookId"] == policy["runbookId"]
        assert payload["timelineMessage"]
        assert payload["eventId"] in payload["timelineMessage"]
        assert payload["confirmedBy"] in payload["timelineMessage"]

        stats = read_stats()
        assert stats["session"] == 1, f"expected 1 session call, saw {stats['session']}"
        assert stats["policy"] == 1, f"expected 1 policy call, saw {stats['policy']}"
        assert stats["prepare"] == 1, f"expected 1 prepare call, saw {stats['prepare']}"
        assert stats["confirm"] == 1, f"expected 1 confirm call, saw {stats['confirm']}"
