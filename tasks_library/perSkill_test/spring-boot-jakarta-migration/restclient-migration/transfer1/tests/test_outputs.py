import subprocess
from pathlib import Path


WORKSPACE = Path("/workspace")
CLIENT_FILE = WORKSPACE / "src/main/java/com/example/billingbridge/client/InvoiceLedgerClient.java"


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
        raise AssertionError("InvoiceLedgerClient must use RestClient")
    if "RestTemplate" in source:
        raise AssertionError("InvoiceLedgerClient must not keep RestTemplate")
    if "LedgerUnavailableException" not in source:
        raise AssertionError("InvoiceLedgerClient must still throw LedgerUnavailableException")
    if "onStatus(HttpStatusCode::is5xxServerError" not in source:
        raise AssertionError("InvoiceLedgerClient should install a 5xx status handler")
    if '.uri("/ledger/invoices/{invoiceId}", invoiceId)' not in source:
        raise AssertionError("Invoice lookup should use a RestClient URI template")
    if source.count(".toBodilessEntity()") < 1:
        raise AssertionError("Acknowledgement POST should finish with toBodilessEntity()")


if __name__ == "__main__":
    main()
