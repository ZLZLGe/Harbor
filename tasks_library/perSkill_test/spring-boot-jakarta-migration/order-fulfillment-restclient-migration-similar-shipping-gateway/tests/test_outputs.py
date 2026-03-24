from pathlib import Path
import subprocess

WORKSPACE = Path("/workspace")
TARGET = WORKSPACE / "src/main/java/com/example/orders/integration/ShippingGatewayClient.java"


def read_target() -> str:
    assert TARGET.exists(), f"Missing target file: {TARGET}"
    return TARGET.read_text()


def test_uses_restclient_not_resttemplate():
    content = read_target()
    assert "RestClient" in content, "ShippingGatewayClient must use RestClient"
    assert "RestTemplate" not in content, "RestTemplate should be removed from ShippingGatewayClient"


def test_keeps_shared_base_url_and_default_json_headers():
    content = read_target()
    assert ".baseUrl(baseUrl)" in content, "RestClient should keep a shared base URL"
    assert "defaultHeader(HttpHeaders.ACCEPT" in content, "RestClient should configure a default Accept header"
    assert "defaultHeader(HttpHeaders.CONTENT_TYPE" in content, "RestClient should configure a default Content-Type header"
    assert "MediaType.APPLICATION_JSON_VALUE" in content, "Default headers should stay JSON-based"


def test_uses_get_post_delete_fluent_calls():
    content = read_target()
    assert ".get()" in content, "Quote lookup should use a GET RestClient call"
    assert ".post()" in content, "Shipment creation should use a POST RestClient call"
    assert ".delete()" in content, "Shipment cancellation should use a DELETE RestClient call"


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
