from __future__ import annotations

from dataclasses import dataclass


class GatewayTimeoutError(RuntimeError):
    """Raised when the upstream billing service times out."""


class GatewayDeclinedError(RuntimeError):
    """Raised when the upstream billing service rejects a charge."""


class BillingDeclinedError(RuntimeError):
    """Raised when a charge is declined and should not be retried."""


class BillingUnavailableError(RuntimeError):
    """Raised when the billing service remains unavailable after retries."""


@dataclass(frozen=True)
class ChargeResult:
    invoice_id: str
    remote_id: str
    amount_cents: int
    status: str
    duplicate: bool
    idempotency_key: str


class BillingProviderClient:
    def create_charge(
        self,
        *,
        invoice_id: str,
        account_id: str,
        amount_cents: int,
        idempotency_key: str,
    ) -> dict[str, object]:
        raise NotImplementedError


class InvoiceBillingGateway:
    def __init__(self, client: BillingProviderClient, max_attempts: int = 3) -> None:
        self._client = client
        self._max_attempts = max_attempts

    def capture_invoice(
        self,
        *,
        invoice_id: str,
        account_id: str,
        amount_cents: int,
        idempotency_key: str,
    ) -> ChargeResult:
        attempts = 0

        while True:
            try:
                payload = self._client.create_charge(
                    invoice_id=invoice_id,
                    account_id=account_id,
                    amount_cents=amount_cents,
                    idempotency_key=idempotency_key,
                )
            except GatewayTimeoutError as exc:
                attempts += 1
                if attempts >= self._max_attempts:
                    raise BillingUnavailableError(
                        f"gateway unavailable after {self._max_attempts} attempts"
                    ) from exc
                continue
            except GatewayDeclinedError as exc:
                raise BillingDeclinedError(f"charge declined: {exc}") from exc

            return ChargeResult(
                invoice_id=invoice_id,
                remote_id=str(payload["charge_id"]),
                amount_cents=amount_cents,
                status=str(payload["status"]),
                duplicate=bool(payload["duplicate"]),
                idempotency_key=idempotency_key,
            )
