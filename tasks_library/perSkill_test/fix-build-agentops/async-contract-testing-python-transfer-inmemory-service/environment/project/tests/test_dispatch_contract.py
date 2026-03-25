import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:8000"


def read_json(path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"content-type": "application/json"},
    )
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def test_service_info_comes_from_local_server():
    payload = read_json("/service-info")

    assert payload["service"] == "dispatch-board"
    assert payload["transport"] == "http"


def test_lookup_ticket_uses_http_endpoint():
    payload = read_json("/tools/lookup_ticket", {"ticket_id": "INC-42"})

    assert payload["ticket"]["team"] == "routing"
    assert payload["ticket"]["severity"] == "high"


def test_run_batch_returns_results_from_server():
    payload = read_json(
        "/batch",
        {
            "calls": [
                {"tool": "list_escalations", "payload": {"team": "routing"}},
                {
                    "tool": "schedule_callback",
                    "payload": {
                        "ticket_id": "INC-42",
                        "owner": "mia",
                        "slot": "2026-03-25T09:30:00Z",
                    },
                },
            ]
        },
    )

    assert payload["results"][0]["tool"] == "list_escalations"
    assert payload["results"][1]["tool"] == "schedule_callback"


def test_unknown_tool_returns_http_error():
    try:
        read_json("/tools/close_ticket", {"ticket_id": "INC-42"})
    except HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("expected close_ticket to fail")
