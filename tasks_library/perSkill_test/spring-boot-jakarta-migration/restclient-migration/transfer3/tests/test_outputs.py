import subprocess
from pathlib import Path


WORKSPACE = Path("/workspace")
CONFIG_FILE = WORKSPACE / "src/main/java/com/example/compliancearchive/config/ComplianceRestClientConfig.java"
CLIENT_FILE = WORKSPACE / "src/main/java/com/example/compliancearchive/client/ComplianceArchiveClient.java"


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

    config_source = CONFIG_FILE.read_text()
    client_source = CLIENT_FILE.read_text()

    if "RestClient" not in config_source:
        raise AssertionError("ComplianceRestClientConfig must define a RestClient bean")
    if "RestTemplate" in config_source:
        raise AssertionError("ComplianceRestClientConfig must not keep RestTemplate")
    if ".baseUrl(baseUrl)" not in config_source:
        raise AssertionError("ComplianceRestClientConfig should set the base URL")
    if 'defaultHeader("X-Compliance-Source", "case-ops")' not in config_source:
        raise AssertionError("ComplianceRestClientConfig should preserve the compliance source header")

    if "RestClient" not in client_source:
        raise AssertionError("ComplianceArchiveClient must use RestClient")
    if "RestTemplate" in client_source:
        raise AssertionError("ComplianceArchiveClient must not keep RestTemplate")
    if '.uri("/cases/{caseId}/archive", caseId)' not in client_source:
        raise AssertionError("Archive POST should use a relative URI")
    if '.uri("/cases/{caseId}/archive-status", caseId)' not in client_source:
        raise AssertionError("Status GET should use a relative URI")


if __name__ == "__main__":
    main()
