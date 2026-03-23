import subprocess
from pathlib import Path


WORKSPACE = Path("/workspace")
CLIENT_FILE = WORKSPACE / "src/main/java/com/example/customerprofile/client/ProfileGatewayClient.java"


def assert_contains(text: str, needle: str, message: str) -> None:
    if needle not in text:
        raise AssertionError(message)


def assert_not_contains(text: str, needle: str, message: str) -> None:
    if needle in text:
        raise AssertionError(message)


def main() -> None:
    result = subprocess.run(
        ["mvn", "-q", "test"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"mvn test failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

    source = CLIENT_FILE.read_text()
    assert_contains(source, "RestClient", "ProfileGatewayClient must use RestClient")
    assert_not_contains(source, "RestTemplate", "ProfileGatewayClient must not keep RestTemplate")
    assert_contains(source, '.uri("/profiles/{customerId}", customerId)', "GET request should use a path template")
    assert_contains(source, ".body(CustomerProfile.class)", "GET request should deserialize CustomerProfile")
    assert_contains(source, ".body(new WelcomeMessageRequest(customerId, templateCode))", "POST request should send the welcome payload")
    if source.count(".toBodilessEntity()") < 2:
        raise AssertionError("POST and DELETE requests should both finish with toBodilessEntity()")


if __name__ == "__main__":
    main()
