from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import db, ledger_client, service


class HoldRequest(BaseModel):
    sku: str
    location: str
    quantity: int = Field(ge=1, le=10)
    hold_seconds: int = Field(ge=1, le=30)
    customer_id: str


class ConfirmRequest(BaseModel):
    hold_id: str
    order_id: str


class CancelRequest(BaseModel):
    hold_id: str
    reason: str | None = None


app = FastAPI(title="checkout-api", version="1.0")


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


def _handle_api_error(exc: service.ApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.get("/health")
def health() -> dict[str, object]:
    try:
        ledger = ledger_client.health()
    except Exception as exc:  # pragma: no cover - surfaced as health failure
        raise HTTPException(status_code=503, detail=f"ledger unavailable: {exc}") from exc
    return {"ok": True, "ledger": ledger}


@app.post("/internal/reset")
def internal_reset() -> dict[str, object]:
    try:
        return service.reset_state()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/internal/state")
def internal_state() -> dict[str, object]:
    try:
        return service.local_state()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/holds")
def create_hold(request: HoldRequest, idempotency_key: str = Header(alias="Idempotency-Key")) -> JSONResponse:
    try:
        payload, status_code = service.create_hold(request.model_dump(), idempotency_key)
    except service.ApiError as exc:
        _handle_api_error(exc)
    return JSONResponse(payload, status_code=status_code)


@app.get("/api/v1/holds/{hold_id}")
def get_hold(hold_id: str) -> dict[str, object]:
    try:
        return service.get_hold(hold_id)
    except service.ApiError as exc:
        _handle_api_error(exc)
    raise AssertionError("unreachable")


@app.get("/api/v1/availability")
def get_availability(
    sku: str = Query(..., min_length=1),
    location: str = Query(..., min_length=1),
) -> dict[str, object]:
    try:
        return service.availability(sku, location)
    except ledger_client.LedgerError as exc:
        raise HTTPException(status_code=502, detail=exc.payload) from exc
    except service.ApiError as exc:
        _handle_api_error(exc)
    raise AssertionError("unreachable")


@app.post("/api/v1/orders/confirm")
def confirm_order(request: ConfirmRequest) -> dict[str, object]:
    try:
        return service.confirm_order(request.hold_id, request.order_id)
    except service.ApiError as exc:
        _handle_api_error(exc)
    raise AssertionError("unreachable")


@app.post("/api/v1/orders/cancel")
def cancel_order(request: CancelRequest) -> dict[str, object]:
    try:
        return service.cancel_order(request.hold_id, request.reason)
    except service.ApiError as exc:
        _handle_api_error(exc)
    raise AssertionError("unreachable")
