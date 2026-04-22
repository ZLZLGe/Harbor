from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from rollout_api.service import build_incident_list, build_summary, health_check


app = FastAPI(title="rollout-summary-api")


@app.get("/healthz")
def healthz() -> JSONResponse:
    ok, detail = health_check()
    if ok:
        return JSONResponse(status_code=200, content={"ok": True})
    return JSONResponse(status_code=503, content={"ok": False, "detail": detail})


@app.get("/api/v1/rollouts/summary")
def summary(region: str = Query(...), service: str = Query(...)) -> dict:
    return build_summary(region=region, service=service)


@app.get("/api/v1/rollouts/incidents")
def incidents(region: str = Query(...), service: str = Query(...)) -> dict:
    return build_incident_list(region=region, service=service)
