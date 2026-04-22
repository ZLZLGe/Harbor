from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Query, Request


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "validation_scenarios.json"
AUDIT_PATH = Path("/tmp/settlement-gateway-audit.json")
TOKEN = os.environ.get("SETTLEMENT_GATEWAY_TOKEN", "settlement-gateway-demo-token")


def load_dataset() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def read_audit() -> list[dict[str, Any]]:
    if not AUDIT_PATH.exists():
        return []
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def write_audit(events: list[dict[str, Any]]) -> None:
    AUDIT_PATH.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")


def append_audit(request: Request, authorized: bool, details: dict[str, Any] | None = None) -> None:
    events = read_audit()
    events.append(
        {
            "path": request.url.path,
            "query": dict(request.query_params),
            "authorized": authorized,
            "details": details or {},
        }
    )
    write_audit(events)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_rows(rows: list[dict[str, Any]], sort_keys: list[str]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for row in rows:
        normalized.append({key: str(value) for key, value in row.items()})
    return sorted(normalized, key=lambda row: tuple(row[key] for key in sort_keys))


def compare_rows(expected: list[dict[str, Any]], actual: list[dict[str, Any]], sort_keys: list[str]) -> list[str]:
    expected_rows = normalize_rows(expected, sort_keys)
    actual_rows = normalize_rows(actual, sort_keys)
    if expected_rows == actual_rows:
        return []

    mismatches: list[str] = []
    if len(expected_rows) != len(actual_rows):
        mismatches.append(
            f"row_count mismatch: expected {len(expected_rows)}, got {len(actual_rows)}"
        )
    for index, (left, right) in enumerate(zip(expected_rows, actual_rows), start=1):
        if left != right:
            mismatches.append(
                f"row {index} mismatch: expected {json.dumps(left, sort_keys=True)}, got {json.dumps(right, sort_keys=True)}"
            )
        if len(mismatches) >= 5:
            break
    if len(actual_rows) > len(expected_rows) and len(mismatches) < 5:
        mismatches.append(
            f"unexpected trailing row: {json.dumps(actual_rows[len(expected_rows)], sort_keys=True)}"
        )
    if len(expected_rows) > len(actual_rows) and len(mismatches) < 5:
        mismatches.append(
            f"missing trailing row: {json.dumps(expected_rows[len(actual_rows)], sort_keys=True)}"
        )
    return mismatches


app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"ok": "true"}


@app.post("/api/v1/reset")
def reset() -> dict[str, bool]:
    write_audit([])
    return {"ok": True}


@app.get("/api/v1/audit")
def audit() -> dict[str, Any]:
    return {"events": read_audit()}


@app.get("/api/v1/integrity")
def integrity() -> dict[str, str]:
    return {
        "server_sha256": file_sha256(ROOT / "server.py"),
        "data_sha256": file_sha256(DATA_PATH),
    }


def require_token(request: Request, supplied: str | None) -> None:
    authorized = supplied == TOKEN
    append_audit(request, authorized)
    if not authorized:
        raise HTTPException(status_code=401, detail="invalid settlement gateway token")


def validate_report(
    *,
    scenario: str,
    report_type: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    dataset = load_dataset()
    try:
        scenario_payload = dataset["scenarios"][scenario]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown scenario: {scenario}") from exc

    expected_rows = scenario_payload[report_type]
    sort_keys = dataset["sort_keys"][report_type]
    mismatches = compare_rows(expected_rows, rows, sort_keys)
    return {
        "accepted": not mismatches,
        "scenario": scenario,
        "report_type": report_type,
        "expected_row_count": len(expected_rows),
        "actual_row_count": len(rows),
        "mismatches": mismatches,
    }


@app.post("/api/v1/validate/daily")
async def validate_daily(
    request: Request,
    scenario: str = Query(...),
    x_settlement_gateway_token: str | None = Header(default=None),
) -> dict[str, Any]:
    require_token(request, x_settlement_gateway_token)
    payload = await request.json()
    rows = payload.get("rows", [])
    result = validate_report(scenario=scenario, report_type="daily", rows=rows)
    append_audit(
        request,
        True,
        {
            "scenario": scenario,
            "report_type": "daily",
            "accepted": result["accepted"],
        },
    )
    return result


@app.post("/api/v1/validate/monthly")
async def validate_monthly(
    request: Request,
    scenario: str = Query(...),
    x_settlement_gateway_token: str | None = Header(default=None),
) -> dict[str, Any]:
    require_token(request, x_settlement_gateway_token)
    payload = await request.json()
    rows = payload.get("rows", [])
    result = validate_report(scenario=scenario, report_type="monthly", rows=rows)
    append_audit(
        request,
        True,
        {
            "scenario": scenario,
            "report_type": "monthly",
            "accepted": result["accepted"],
        },
    )
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8320, log_level="warning")
