#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${TASK_PROJECT_ROOT:-/workspace/billing-relay}"

mkdir -p "$PROJECT_ROOT/tests" "$PROJECT_ROOT/reports"

cat <<'EOF' > "$PROJECT_ROOT/tests/test_billing_gateway.py"
from unittest.mock import create_autospec

import pytest

from billing_relay import (
    BillingDeclinedError,
    BillingProviderClient,
    BillingUnavailableError,
    ChargeResult,
    GatewayDeclinedError,
    GatewayTimeoutError,
    InvoiceBillingGateway,
)


@pytest.fixture
def mock_client() -> BillingProviderClient:
    return create_autospec(BillingProviderClient, instance=True)


@pytest.fixture
def gateway(mock_client: BillingProviderClient) -> InvoiceBillingGateway:
    return InvoiceBillingGateway(mock_client)


def test_capture_invoice_retries_until_third_attempt_success(
    gateway: InvoiceBillingGateway,
    mock_client: BillingProviderClient,
) -> None:
    mock_client.create_charge.side_effect = [
        GatewayTimeoutError("temporary timeout"),
        GatewayTimeoutError("temporary timeout"),
        {"charge_id": "ch_900", "status": "captured", "duplicate": False},
    ]

    result = gateway.capture_invoice(
        invoice_id="inv-100",
        account_id="acct-9",
        amount_cents=4200,
        idempotency_key="idem-inv-100",
    )

    assert result == ChargeResult(
        invoice_id="inv-100",
        remote_id="ch_900",
        amount_cents=4200,
        status="captured",
        duplicate=False,
        idempotency_key="idem-inv-100",
    )
    assert mock_client.create_charge.call_count == 3
    keys = [
        call.kwargs["idempotency_key"] for call in mock_client.create_charge.call_args_list
    ]
    assert keys == ["idem-inv-100", "idem-inv-100", "idem-inv-100"]


def test_capture_invoice_maps_decline_without_retry(
    gateway: InvoiceBillingGateway,
    mock_client: BillingProviderClient,
) -> None:
    mock_client.create_charge.side_effect = GatewayDeclinedError("card expired")

    with pytest.raises(BillingDeclinedError, match="card expired"):
        gateway.capture_invoice(
            invoice_id="inv-101",
            account_id="acct-9",
            amount_cents=4200,
            idempotency_key="idem-inv-101",
        )

    assert mock_client.create_charge.call_count == 1


def test_capture_invoice_raises_unavailable_after_three_timeouts(
    gateway: InvoiceBillingGateway,
    mock_client: BillingProviderClient,
) -> None:
    mock_client.create_charge.side_effect = [
        GatewayTimeoutError("temporary timeout"),
        GatewayTimeoutError("temporary timeout"),
        GatewayTimeoutError("temporary timeout"),
    ]

    with pytest.raises(BillingUnavailableError, match="3 attempts"):
        gateway.capture_invoice(
            invoice_id="inv-102",
            account_id="acct-9",
            amount_cents=4200,
            idempotency_key="idem-inv-102",
        )

    assert mock_client.create_charge.call_count == 3


def test_capture_invoice_preserves_idempotent_repeat_observation(
    gateway: InvoiceBillingGateway,
    mock_client: BillingProviderClient,
) -> None:
    mock_client.create_charge.side_effect = [
        {"charge_id": "ch_901", "status": "captured", "duplicate": False},
        {"charge_id": "ch_901", "status": "captured", "duplicate": True},
    ]

    first = gateway.capture_invoice(
        invoice_id="inv-103",
        account_id="acct-9",
        amount_cents=5100,
        idempotency_key="idem-inv-103",
    )
    second = gateway.capture_invoice(
        invoice_id="inv-103",
        account_id="acct-9",
        amount_cents=5100,
        idempotency_key="idem-inv-103",
    )

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.remote_id == first.remote_id
    assert mock_client.create_charge.call_count == 2
EOF

cat <<'EOF' > "$PROJECT_ROOT/reports/mock_retry_audit.txt"
Mock Retry Audit
suite_status: complete
tested_entrypoint: InvoiceBillingGateway.capture_invoice
mock_boundary: create_charge
retry_success_attempts: 3
decline_mapping: BillingDeclinedError
idempotent_repeat_observed: true
note: no real billing service was contacted
EOF

cd "$PROJECT_ROOT"
pytest -q tests/test_billing_gateway.py
