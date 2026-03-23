import subprocess
from pathlib import Path


WORKSPACE = Path("/workspace")
CLIENT_FILE = WORKSPACE / "src/main/java/com/example/logisticsquotes/client/CarrierQuoteClient.java"


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
    if "RestClient" not in source:
        raise AssertionError("CarrierQuoteClient must use RestClient")
    if "RestTemplate" in source:
        raise AssertionError("CarrierQuoteClient must not keep RestTemplate")
    if "uri(uriBuilder ->" not in source:
        raise AssertionError("CarrierQuoteClient should use a URI builder for query parameters")
    if "new ParameterizedTypeReference<List<CarrierQuote>>()" not in source:
        raise AssertionError("CarrierQuoteClient must preserve the generic list response type")
    if '.uri("/quotes/requests/{quoteRequestId}", quoteRequestId)' not in source:
        raise AssertionError("Quote cancellation should use a RestClient URI template")
    if ".toBodilessEntity()" not in source:
        raise AssertionError("Quote cancellation should finish with toBodilessEntity()")


if __name__ == "__main__":
    main()
