from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8080"
RATE_URL = "http://127.0.0.1:9101"
BOOKING_URL = "http://127.0.0.1:9102"
ALPHA = {"X-Partner-Key": "pk_live_alpha"}
BETA = {"X-Partner-Key": "pk_live_beta"}
THROTTLE = {"X-Partner-Key": "pk_live_throttle"}


def wait_for_gateway() -> None:
    for _ in range(80):
        try:
            if requests.get(f"{BASE_URL}/health", timeout=0.5).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise AssertionError("gateway did not become healthy")


def reset_downstreams() -> None:
    requests.post(f"{RATE_URL}/internal/test/reset", timeout=2).raise_for_status()
    requests.post(f"{BOOKING_URL}/internal/test/reset", timeout=2).raise_for_status()


def set_rate_mode(mode: str) -> None:
    requests.post(f"{RATE_URL}/internal/test/mode", json={"mode": mode}, timeout=2).raise_for_status()


def set_booking_mode(mode: str) -> None:
    requests.post(f"{BOOKING_URL}/internal/test/mode", json={"mode": mode}, timeout=2).raise_for_status()


def rate_calls() -> list[dict]:
    return requests.get(f"{RATE_URL}/internal/test/ledger", timeout=2).json()["calls"]


def booking_calls() -> list[dict]:
    return requests.get(f"{BOOKING_URL}/internal/test/ledger", timeout=2).json()["calls"]


def assert_error(resp: requests.Response, status: int, code: str | None = None) -> dict:
    assert resp.status_code == status, resp.text
    payload = resp.json()
    assert set(payload) == {"error"}, payload
    assert isinstance(payload["error"].get("code"), str)
    assert isinstance(payload["error"].get("message"), str)
    assert isinstance(payload["error"].get("details"), list)
    if code:
        assert payload["error"]["code"] == code, payload
    return payload


def assert_success_envelope(resp: requests.Response, status: int = 200) -> dict:
    assert resp.status_code == status, resp.text
    payload = resp.json()
    assert set(payload) == {"data", "meta", "links"}, payload
    assert isinstance(payload["meta"], dict), payload
    assert isinstance(payload["links"], dict), payload
    return payload


def assert_rate_limit_headers(resp: requests.Response, expected_limit: int | None = None) -> None:
    for header in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
        assert header in resp.headers, f"missing {header}: {dict(resp.headers)}"
        assert resp.headers[header].isdigit(), f"{header} must be numeric"
    if expected_limit is not None:
        assert int(resp.headers["X-RateLimit-Limit"]) == expected_limit
    assert int(resp.headers["X-RateLimit-Remaining"]) >= 0
    assert int(resp.headers["X-RateLimit-Reset"]) > 0


def quote_params(**overrides):
    params = {
        "originPostal": "94105",
        "destinationPostal": "10001",
        "weightGrams": "1200",
        "shipDate": "2026-05-04",
    }
    params.update(overrides)
    return params


def get_quote(headers=None, **params):
    reset_downstreams()
    resp = requests.get(
        f"{BASE_URL}/api/v1/shipping-quotes",
        params=quote_params(**params),
        headers=headers or ALPHA,
        timeout=3,
    )
    payload = assert_success_envelope(resp)
    assert payload["data"], payload
    return payload["data"][0]


def immutable_hashes_match(kind: str) -> bool:
    expected = Path(f"/opt/shipping-api-{kind}.sha256")
    if not expected.exists():
        raise AssertionError(f"missing hash manifest {expected}")
    if kind == "data":
        root = Path("/app/workspace/data")
    elif kind == "contracts":
        root = Path("/app/workspace/contracts")
    elif kind == "services":
        root = Path("/app/workspace/services")
    else:
        raise AssertionError(kind)
    output = subprocess.check_output(
        "find . -type f -print0 | sort -z | xargs -0 sha256sum",
        cwd=root,
        shell=True,
        text=True,
    )
    expected_lines = []
    for line in expected.read_text(encoding="utf-8").splitlines():
        digest, path = line.split(maxsplit=1)
        expected_lines.append(f"{digest}  ./{Path(path).relative_to(root)}")
    return output.strip().splitlines() == expected_lines
