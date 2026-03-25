from __future__ import annotations

import base64
import json
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


WORKSPACE = Path("/workspace")
SECURITY_FILE = WORKSPACE / "src/main/java/com/example/opsgateway/security/GatewaySecurityChains.java"
BASE_URL = "http://127.0.0.1:18080"


def _request(path: str, headers: dict[str, str] | None = None) -> tuple[int, str]:
    request = Request(f"{BASE_URL}{path}", headers=headers or {})
    try:
        with urlopen(request, timeout=5) as response:
            return response.getcode(), response.read().decode()
    except HTTPError as error:
        return error.code, error.read().decode()


def _basic_auth(username: str, password: str) -> str:
    raw = f"{username}:{password}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def test_gateway_security_file_uses_component_chains():
    content = SECURITY_FILE.read_text()

    assert content.count("SecurityFilterChain") >= 3
    assert "requestMatchers" in content
    assert "WebSecurityConfigurerAdapter" not in content
    assert "EnableGlobalMethodSecurity" not in content
    assert "antMatchers" not in content


def test_workspace_unit_tests_pass():
    result = subprocess.run(
        ["mvn", "-q", "test"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_runtime_endpoint_contracts():
    log_path = Path("/tmp/opsgateway-runtime.log")
    with log_path.open("w+") as log_file:
        process = subprocess.Popen(
            ["mvn", "-q", "-DskipTests", "spring-boot:run"],
            cwd=WORKSPACE,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            deadline = time.time() + 90
            last_error = None
            while time.time() < deadline:
                try:
                    status, body = _request("/actuator/health")
                    if status == 200 and '"status":"UP"' in body:
                        break
                except (URLError, ConnectionError) as error:  # pragma: no cover
                    last_error = error
                time.sleep(1)
            else:
                process.terminate()
                process.wait(timeout=20)
                logs = log_path.read_text()
                raise AssertionError(f"gateway failed to start: {last_error}\n{logs}")

            status, body = _request("/docs/index.html")
            assert status == 200
            assert "Gateway Runbook" in body

            status, body = _request("/internal/ops/status")
            assert status == 401, body

            status, body = _request(
                "/internal/ops/status",
                {"Authorization": _basic_auth("viewer", "viewer-pass")},
            )
            assert status == 403, body

            status, body = _request(
                "/internal/ops/status",
                {"Authorization": _basic_auth("opsbot", "ops-pass")},
            )
            assert status == 200, body
            payload = json.loads(body)
            assert payload["surface"] == "internal"
            assert payload["principal"] == "opsbot"

            status, body = _request("/api/v1/transfers")
            assert status == 401, body

            status, body = _request(
                "/api/v1/transfers",
                {"Authorization": _basic_auth("opsbot", "ops-pass")},
            )
            assert status == 401, body

            status, body = _request(
                "/api/v1/transfers",
                {"Authorization": "Bearer ops-api-token"},
            )
            assert status == 200, body
            payload = json.loads(body)
            assert payload["surface"] == "api"
            assert payload["principal"] == "api-robot"
            assert payload["mode"] == "stateless"
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=20)
