from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Query, Request


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "release_snapshot.json"
AUDIT_PATH = Path("/tmp/release-broker-audit.json")
TOKEN = os.environ.get("RELEASE_BROKER_TOKEN", "release-broker-demo-token")


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
        raise HTTPException(status_code=401, detail="invalid broker token")


@app.get("/api/v1/release-candidates")
def release_candidates(
    request: Request,
    x_release_broker_token: str | None = Header(default=None),
) -> dict[str, Any]:
    require_token(request, x_release_broker_token)
    dataset = load_dataset()
    return {
        "source": "broker",
        "release_id": dataset["release_id"],
        "generated_at": dataset["generated_at"],
        "candidates": dataset["candidates"],
    }


@app.get("/api/v1/provenance")
def provenance(
    request: Request,
    release_id: str = Query(...),
    x_release_broker_token: str | None = Header(default=None),
) -> dict[str, Any]:
    require_token(request, x_release_broker_token)
    dataset = load_dataset()
    if release_id != dataset["release_id"]:
        raise HTTPException(status_code=404, detail="unknown release id")
    return {
        "source": "broker",
        "release_id": dataset["release_id"],
        "records": dataset["provenance"],
    }


@app.get("/api/v1/promotion-plan")
def promotion_plan(
    request: Request,
    release_id: str = Query(...),
    x_release_broker_token: str | None = Header(default=None),
) -> dict[str, Any]:
    require_token(request, x_release_broker_token)
    dataset = load_dataset()
    if release_id != dataset["release_id"]:
        raise HTTPException(status_code=404, detail="unknown release id")
    return {
        "source": "broker",
        "release_id": dataset["release_id"],
        "plan_id": dataset["promotion_plan"]["plan_id"],
        "promotions": dataset["promotion_plan"]["promotions"],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8310, log_level="warning")
