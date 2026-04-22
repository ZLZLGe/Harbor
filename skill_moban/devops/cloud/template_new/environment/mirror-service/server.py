from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn


EXPECTED_CLIENT_ID = "rollout-reader-client"
EXPECTED_SCOPE = "api://rollout-mirror/.default"
DATA_PATH = Path(os.environ.get("MIRROR_DATA_PATH", "/services/mirror-service/data/incidents_snapshot.json"))
AUDIT_PATH = Path(os.environ.get("MIRROR_AUDIT_PATH", "/tmp/mirror_audit_log.json"))

app = FastAPI(title="hidden-mirror-service")


def _load_snapshot() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _read_audit() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def _write_audit(events: list[dict]) -> None:
    AUDIT_PATH.write_text(json.dumps(events, indent=2), encoding="utf-8")


def _append_audit(event: dict) -> None:
    events = _read_audit()
    events.append(event)
    _write_audit(events)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/v1/incidents")
def get_incidents(
    region: str | None = Query(default=None),
    service: str | None = Query(default=None),
    x_managed_identity_client: str = Header(default=""),
    x_mirror_scope: str = Header(default=""),
) -> dict:
    authorized = x_managed_identity_client == EXPECTED_CLIENT_ID and x_mirror_scope == EXPECTED_SCOPE

    _append_audit(
        {
            "ts": time.time(),
            "region": region,
            "service": service,
            "authorized": authorized,
            "client_id": x_managed_identity_client,
            "scope": x_mirror_scope,
        }
    )

    if not authorized:
        raise HTTPException(status_code=403, detail="mirror authorization failed")

    snapshot = _load_snapshot()
    items = snapshot["items"]

    if region:
        items = [item for item in items if item["region"] == region]
    if service:
        items = [item for item in items if item["service_slug"] == service]

    return {
        "snapshot_id": snapshot["snapshot_id"],
        "generated_at": snapshot["generated_at"],
        "items": items,
    }


@app.post("/__admin/reset")
def reset_audit() -> dict:
    _write_audit([])
    return {"ok": True}


@app.get("/__admin/audit")
def get_audit() -> dict:
    return {"events": _read_audit()}


if __name__ == "__main__":
    port = int(os.environ.get("MIRROR_PORT", "8320"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
