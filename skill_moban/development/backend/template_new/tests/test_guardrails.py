from __future__ import annotations

import requests

from verifier_utils import (
    ALPHA,
    BASE_URL,
    assert_error,
    assert_success_envelope,
    booking_calls,
    get_quote,
    immutable_hashes_match,
    quote_params,
    rate_calls,
    reset_downstreams,
    set_booking_mode,
    set_rate_mode,
)


def test_immutable_inputs_and_downstream_services_are_not_modified():
    assert immutable_hashes_match("data")
    assert immutable_hashes_match("contracts")
    assert immutable_hashes_match("services")


def test_quote_endpoint_uses_real_rate_downstream_and_handles_failures():
    reset_downstreams()
    resp = requests.get(
        f"{BASE_URL}/api/v1/shipping-quotes",
        params=quote_params(destinationPostal="60601", sort="-eta"),
        headers=ALPHA,
        timeout=3,
    )
    payload = assert_success_envelope(resp)
    assert payload["data"]
    calls = rate_calls()
    assert len(calls) == 1
    assert calls[0]["payload"]["destinationPostal"] == "60601"

    set_rate_mode("invalid")
    invalid = requests.get(f"{BASE_URL}/api/v1/shipping-quotes", params=quote_params(), headers=ALPHA, timeout=3)
    assert_error(invalid, 502)

    set_rate_mode("timeout")
    timeout = requests.get(f"{BASE_URL}/api/v1/shipping-quotes", params=quote_params(), headers=ALPHA, timeout=4)
    assert_error(timeout, 503)
    assert timeout.headers.get("Retry-After")
    set_rate_mode("normal")


def test_booking_endpoint_uses_real_booking_downstream_and_handles_failures():
    quote = get_quote(destinationPostal="60601", weightGrams="2400", serviceLevel="standard", carrier="roadline")
    body = {
        "quoteId": quote["quoteId"],
        "orderId": "ord_alpha_1002",
        "labelFormat": "zpl",
        "metadata": {"guardrail": True},
    }

    set_booking_mode("invalid")
    invalid = requests.post(
        f"{BASE_URL}/api/v1/shipments",
        json=body,
        headers={**ALPHA, "Idempotency-Key": "booking-invalid-1"},
        timeout=3,
    )
    assert_error(invalid, 502)

    set_booking_mode("normal")
    reset_downstreams()
    quote = get_quote(destinationPostal="60601", weightGrams="2400", serviceLevel="standard", carrier="roadline")
    body["quoteId"] = quote["quoteId"]
    created = requests.post(
        f"{BASE_URL}/api/v1/shipments",
        json=body,
        headers={**ALPHA, "Idempotency-Key": "booking-real-1"},
        timeout=3,
    )
    assert_success_envelope(created, 201)
    assert len(booking_calls()) == 1
