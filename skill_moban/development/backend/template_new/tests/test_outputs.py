from __future__ import annotations

import requests

from verifier_utils import (
    ALPHA,
    BASE_URL,
    BETA,
    BOOKING_URL,
    THROTTLE,
    assert_error,
    assert_rate_limit_headers,
    assert_success_envelope,
    booking_calls,
    get_quote,
    quote_params,
    rate_calls,
    reset_downstreams,
)


def test_auth_validation_and_error_contracts():
    resp = requests.get(f"{BASE_URL}/api/v1/shipping-quotes", params=quote_params(), timeout=3)
    assert_error(resp, 401, "unauthorized")

    resp = requests.get(
        f"{BASE_URL}/api/v1/shipping-quotes",
        params=quote_params(weightGrams="not-an-int"),
        headers=ALPHA,
        timeout=3,
    )
    assert_error(resp, 400, "bad_request")

    resp = requests.get(
        f"{BASE_URL}/api/v1/shipping-quotes",
        params=quote_params(weightGrams="-1"),
        headers=ALPHA,
        timeout=3,
    )
    payload = assert_error(resp, 422, "validation_error")
    assert any(detail["field"] == "weightGrams" for detail in payload["error"]["details"])

    resp = requests.get(
        f"{BASE_URL}/api/v1/shipping-quotes",
        params=quote_params(shipDate="05/04/2026"),
        headers=ALPHA,
        timeout=3,
    )
    assert_error(resp, 422, "validation_error")

    resp = requests.post(
        f"{BASE_URL}/api/v1/shipments",
        data="{bad-json",
        headers={**ALPHA, "Content-Type": "application/json", "Idempotency-Key": "bad-json-1"},
        timeout=3,
    )
    assert_error(resp, 400, "bad_request")


def test_quotes_sorting_pagination_and_partner_authorization():
    reset_downstreams()
    resp = requests.get(
        f"{BASE_URL}/api/v1/shipping-quotes",
        params=quote_params(sort="price", **{"page[limit]": "2"}),
        headers=ALPHA,
        timeout=3,
    )
    payload = assert_success_envelope(resp)
    assert_rate_limit_headers(resp, expected_limit=80)
    assert isinstance(payload["data"], list)
    assert payload["meta"] == {"count": 2, "hasMore": True}
    assert "originPostal=94105" in payload["links"]["self"]
    assert "page%5Bcursor%5D=" in payload["links"]["next"] or "page[cursor]=" in payload["links"]["next"]
    prices = [item["price"]["amount"] for item in payload["data"]]
    assert prices == sorted(prices)
    assert all(item["serviceLevel"] in {"standard", "expedited"} for item in payload["data"])
    assert len(rate_calls()) == 1

    resp2 = requests.get(BASE_URL + payload["links"]["next"], headers=ALPHA, timeout=3)
    second = assert_success_envelope(resp2)
    first_ids = {item["quoteId"] for item in payload["data"]}
    second_ids = {item["quoteId"] for item in second["data"]}
    assert first_ids.isdisjoint(second_ids)

    resp = requests.get(
        f"{BASE_URL}/api/v1/shipping-quotes",
        params=quote_params(serviceLevel="overnight"),
        headers=ALPHA,
        timeout=3,
    )
    assert_error(resp, 403, "forbidden")

    resp = requests.get(
        f"{BASE_URL}/api/v1/shipping-quotes",
        params=quote_params(carrier="skybridge"),
        headers=BETA,
        timeout=3,
    )
    assert_error(resp, 403, "forbidden")


def test_shipment_create_replay_conflict_and_read_isolation():
    quote = get_quote(weightGrams="1180", serviceLevel="standard", carrier="roadline")
    body = {
        "quoteId": quote["quoteId"],
        "orderId": "ord_alpha_1001",
        "labelFormat": "pdf",
        "metadata": {"warehouse": "SFO-3", "batch": "qa"},
    }
    headers = {**ALPHA, "Idempotency-Key": "idem-alpha-001"}

    resp = requests.post(f"{BASE_URL}/api/v1/shipments", json=body, headers=headers, timeout=3)
    payload = assert_success_envelope(resp, 201)
    assert_rate_limit_headers(resp, expected_limit=80)
    assert resp.headers["Location"].endswith(payload["data"]["shipmentId"])
    assert payload["data"]["metadata"] == body["metadata"]
    assert payload["data"]["quote"]["quoteId"] == quote["quoteId"]
    assert len(booking_calls()) == 1

    replay = requests.post(f"{BASE_URL}/api/v1/shipments", json=body, headers=headers, timeout=3)
    assert replay.status_code in {200, 201}, replay.text
    replay_payload = assert_success_envelope(replay, replay.status_code)
    assert_rate_limit_headers(replay, expected_limit=80)
    assert replay_payload["data"]["shipmentId"] == payload["data"]["shipmentId"]
    assert len(booking_calls()) == 1

    conflict = requests.post(
        f"{BASE_URL}/api/v1/shipments",
        json={**body, "labelFormat": "zpl"},
        headers=headers,
        timeout=3,
    )
    assert_error(conflict, 409, "idempotency_conflict")

    read = requests.get(f"{BASE_URL}/api/v1/shipments/{payload['data']['shipmentId']}", headers=ALPHA, timeout=3)
    read_payload = assert_success_envelope(read)
    assert_rate_limit_headers(read, expected_limit=80)
    assert read_payload["data"]["shipmentId"] == payload["data"]["shipmentId"]

    blocked = requests.get(f"{BASE_URL}/api/v1/shipments/{payload['data']['shipmentId']}", headers=BETA, timeout=3)
    assert_error(blocked, 404, "not_found")


def test_partner_rate_limit_uses_429_and_retry_after():
    for idx in range(2):
        resp = requests.get(
            f"{BASE_URL}/api/v1/shipping-quotes",
            params=quote_params(destinationPostal="11201"),
            headers=THROTTLE,
            timeout=3,
        )
        assert_success_envelope(resp)
        assert_rate_limit_headers(resp, expected_limit=2)
    limited = requests.get(
        f"{BASE_URL}/api/v1/shipping-quotes",
        params=quote_params(destinationPostal="11201"),
        headers=THROTTLE,
        timeout=3,
    )
    assert_error(limited, 429, "rate_limit_exceeded")
    assert int(limited.headers["Retry-After"]) > 0
    assert_rate_limit_headers(limited, expected_limit=2)
