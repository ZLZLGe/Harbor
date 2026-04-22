from __future__ import annotations

import atexit
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
TEMPLATE_PATH = Path(os.environ.get("DEPLOYMENT_TEMPLATE_PATH", str(WORKSPACE_ROOT / "infra/containerapp.template.json")))
ROLL_OUT_API_ROOT = WORKSPACE_ROOT / "rollout-api"
PUBLIC_APP_HOST = "127.0.0.1"
MIRROR_BASE_URL = os.environ.get("MIRROR_API_URL", "http://127.0.0.1:8320")
CONTROL_PLANE_CODE_PATH = Path(os.environ.get("CONTROL_PLANE_PATH", "/services/control-plane/server.py"))
MIRROR_SERVER_PATH = Path(os.environ.get("MIRROR_SERVER_PATH", "/services/mirror-service/server.py"))
MIRROR_DATA_PATH = Path(os.environ.get("MIRROR_DATA_PATH", "/services/mirror-service/data/incidents_snapshot.json"))


app = FastAPI(title="local-control-plane")


class RuntimeState:
    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.current_env: dict[str, str] = {}
        self.events: list[dict[str, Any]] = []
        self.issues: list[dict[str, Any]] = []
        self.healthy = False
        self.generation = 0
        self.internal_port = 9200
        self.readiness_path = "/healthz"
        self.active_revision = "none"

    def add_event(self, code: str, detail: str, *, level: str = "info") -> None:
        self.events.append(
            {
                "ts": time.time(),
                "level": level,
                "code": code,
                "detail": detail,
            }
        )

    def stop_process(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None

    def reset(self) -> None:
        self.stop_process()
        self.current_env = {}
        self.events = []
        self.issues = []
        self.healthy = False
        self.active_revision = "none"

    def status(self) -> dict[str, Any]:
        process_running = self.process is not None and self.process.poll() is None
        return {
            "healthy": self.healthy,
            "generation": self.generation,
            "active_revision": self.active_revision,
            "process_running": process_running,
            "process_pid": self.process.pid if process_running else None,
            "issues": self.issues,
            "events": self.events[-20:],
        }


STATE = RuntimeState()


def _load_template() -> dict[str, Any]:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((PUBLIC_APP_HOST, 0))
        return int(sock.getsockname()[1])


def _resolve_env(template: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]], int, str]:
    properties = template["properties"]
    configuration = properties["configuration"]
    container = properties["template"]["containers"][0]
    secrets = {item["name"]: item["value"] for item in configuration.get("secrets", [])}
    issues: list[dict[str, Any]] = []
    resolved_env: dict[str, str] = {}

    for item in container.get("env", []):
        name = item["name"]
        if "value" in item:
            resolved_env[name] = str(item["value"])
            continue
        secret_ref = item.get("secretRef")
        if secret_ref not in secrets:
            issues.append(
                {
                    "severity": "blocking",
                    "code": "UNRESOLVED_SECRET_REF",
                    "detail": f"env {name} references missing secret {secret_ref}",
                }
            )
            continue
        resolved_env[name] = str(secrets[secret_ref])

    port = int(resolved_env.get("PORT", "9200"))
    ingress_target_port = int(configuration["ingress"]["targetPort"])
    readiness_path = properties["template"]["probes"]["readiness"]["path"]

    if ingress_target_port != port:
        issues.append(
            {
                "severity": "blocking",
                "code": "INGRESS_TARGET_PORT_MISMATCH",
                "detail": f"ingress targetPort {ingress_target_port} does not match container PORT {port}",
            }
        )

    if readiness_path != "/healthz":
        issues.append(
            {
                "severity": "blocking",
                "code": "READINESS_PATH_MISMATCH",
                "detail": f"readiness path {readiness_path} does not match the expected public health path /healthz",
            }
        )

    return resolved_env, issues, port, readiness_path


def _start_public_app(env_values: dict[str, str], port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(env_values)
    env["PYTHONPATH"] = str(ROLL_OUT_API_ROOT)
    env["PORT"] = str(port)
    log_file = open("/tmp/rollout-api.log", "w", encoding="utf-8")
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "rollout_api.main:app",
            "--host",
            PUBLIC_APP_HOST,
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(ROLL_OUT_API_ROOT),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _probe_readiness(port: int, readiness_path: str) -> tuple[bool, str]:
    deadline = time.time() + 20
    url = f"http://{PUBLIC_APP_HOST}:{port}{readiness_path}"

    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True, "revision health probe succeeded"
            detail = f"probe returned {response.status_code}: {response.text[:200]}"
        except Exception as exc:  # noqa: BLE001
            detail = f"probe failed: {exc}"
        time.sleep(0.5)

    return False, detail


def _probe_readiness_once(port: int, readiness_path: str) -> tuple[bool, str]:
    url = f"http://{PUBLIC_APP_HOST}:{port}{readiness_path}"
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            return True, "revision health probe succeeded"
        return False, f"probe returned {response.status_code}: {response.text[:200]}"
    except Exception as exc:  # noqa: BLE001
        return False, f"probe failed: {exc}"


def _mirror_audit() -> dict[str, Any]:
    response = requests.get(f"{MIRROR_BASE_URL}/__admin/audit", timeout=5)
    response.raise_for_status()
    return response.json()


def _mirror_reset() -> None:
    requests.post(f"{MIRROR_BASE_URL}/__admin/reset", timeout=5).raise_for_status()


def _deployment_unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "revision_unhealthy",
            "active_revision": STATE.active_revision,
            "issues": STATE.issues,
        },
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _proxy_to_public_app(path: str, query_params: dict[str, str | None]) -> JSONResponse:
    if not STATE.healthy:
        return _deployment_unavailable()

    url = f"http://{PUBLIC_APP_HOST}:{STATE.internal_port}{path}"
    response = requests.get(url, params={k: v for k, v in query_params.items() if v is not None}, timeout=10)
    return JSONResponse(status_code=response.status_code, content=response.json())


@app.on_event("shutdown")
def _on_shutdown() -> None:
    STATE.stop_process()


@atexit.register
def _cleanup() -> None:
    STATE.stop_process()


@app.get("/__control/status")
def status() -> dict[str, Any]:
    return STATE.status()


@app.get("/__control/events")
def events() -> dict[str, Any]:
    return {"events": STATE.events}


@app.get("/__control/preflight")
def preflight() -> dict[str, Any]:
    template = _load_template()
    _, issues, port, readiness_path = _resolve_env(template)
    return {
        "template_path": str(TEMPLATE_PATH),
        "port": port,
        "readiness_path": readiness_path,
        "issues": issues,
    }


@app.post("/__control/reset")
def reset() -> dict[str, Any]:
    STATE.reset()
    _mirror_reset()
    return {"ok": True, "status": STATE.status()}


@app.post("/__control/apply")
def apply() -> dict[str, Any]:
    STATE.stop_process()
    template = _load_template()
    env_values, issues, port, readiness_path = _resolve_env(template)

    STATE.generation += 1
    STATE.active_revision = f"rollout-summary--gen-{STATE.generation}"
    STATE.current_env = env_values
    STATE.internal_port = port
    STATE.readiness_path = readiness_path
    STATE.issues = issues.copy()
    STATE.events = []

    for issue in issues:
        STATE.add_event(issue["code"], issue["detail"], level="error")

    STATE.process = _start_public_app(env_values, port)
    STATE.add_event("REVISION_START", f"started public app on {PUBLIC_APP_HOST}:{port}")

    time.sleep(1.0)

    if STATE.process.poll() is not None:
        STATE.healthy = False
        STATE.issues.append(
            {
                "severity": "blocking",
                "code": "APP_PROCESS_EXITED",
                "detail": "public app exited before readiness completed",
            }
        )
        STATE.add_event("APP_PROCESS_EXITED", "public app exited before readiness completed", level="error")
        return {"ok": True, "status": STATE.status()}

    if any(issue["severity"] == "blocking" for issue in STATE.issues):
        ready, detail = _probe_readiness_once(port, readiness_path)
    else:
        ready, detail = _probe_readiness(port, readiness_path)
    if not ready:
        STATE.healthy = False
        STATE.issues.append(
            {
                "severity": "blocking",
                "code": "READINESS_PROBE_FAILED",
                "detail": detail,
            }
        )
        STATE.add_event("READINESS_PROBE_FAILED", detail, level="error")
    elif any(issue["severity"] == "blocking" for issue in STATE.issues):
        STATE.healthy = False
        STATE.add_event("REVISION_UNHEALTHY", "revision blocked by preflight issues", level="error")
    else:
        STATE.healthy = True
        STATE.add_event("REVISION_HEALTHY", "revision passed health checks")

    return {"ok": True, "status": STATE.status()}


@app.get("/__control/mirror-audit")
def mirror_audit() -> dict[str, Any]:
    return _mirror_audit()


@app.get("/__control/integrity")
def integrity() -> dict[str, str]:
    return {
        "control_plane_sha256": _sha256(CONTROL_PLANE_CODE_PATH),
        "mirror_server_sha256": _sha256(MIRROR_SERVER_PATH),
        "mirror_data_sha256": _sha256(MIRROR_DATA_PATH),
    }


@app.get("/healthz")
def public_health() -> JSONResponse:
    return _proxy_to_public_app("/healthz", {})


@app.get("/api/v1/rollouts/summary")
def public_summary(
    region: str = Query(...),
    service: str = Query(...),
) -> JSONResponse:
    return _proxy_to_public_app("/api/v1/rollouts/summary", {"region": region, "service": service})


@app.get("/api/v1/rollouts/incidents")
def public_incidents(
    region: str = Query(...),
    service: str = Query(...),
) -> JSONResponse:
    return _proxy_to_public_app("/api/v1/rollouts/incidents", {"region": region, "service": service})


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8300, log_level="warning")
