from pathlib import Path
import subprocess

WORKSPACE = Path("/workspace")
TARGET = WORKSPACE / "src/main/java/com/example/incident/client/IncidentBridgeClient.java"


def read_target() -> str:
    assert TARGET.exists(), f"Missing target file: {TARGET}"
    return TARGET.read_text()


def test_uses_restclient_and_removes_resttemplate():
    content = read_target()
    assert "RestClient" in content, "IncidentBridgeClient must use RestClient"
    assert "RestTemplate" not in content, "RestTemplate should be removed from IncidentBridgeClient"


def test_keeps_shared_configuration_and_fluent_calls():
    content = read_target()
    assert ".baseUrl(baseUrl)" in content, "RestClient should keep a shared base URL"
    assert "defaultHeader(HttpHeaders.ACCEPT" in content, "RestClient should configure a default Accept header"
    assert "defaultHeader(HttpHeaders.CONTENT_TYPE" in content, "RestClient should configure a default Content-Type header"
    assert ".get()" in content, "Incident polling should use a GET RestClient call"
    assert ".post()" in content, "Follow-up ticket creation should use a POST RestClient call"


def test_uses_status_handlers_for_domain_exception_mapping():
    content = read_target()
    assert ".defaultStatusHandler(" in content or ".onStatus(" in content, "Status handlers should replace the old ResponseErrorHandler"
    assert "IncidentFeedMissingException" in content, "404 should map to IncidentFeedMissingException"
    assert "IncidentRateLimitedException" in content, "429 should map to IncidentRateLimitedException"
    assert "IncidentBridgeServerException" in content, "5xx should map to IncidentBridgeServerException"
    assert "Retry-After" in content, "429 handling should preserve the Retry-After header"


def test_maven_compile():
    result = subprocess.run(
        ["mvn", "-q", "clean", "compile"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_maven_test():
    result = subprocess.run(
        ["mvn", "-q", "test"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
