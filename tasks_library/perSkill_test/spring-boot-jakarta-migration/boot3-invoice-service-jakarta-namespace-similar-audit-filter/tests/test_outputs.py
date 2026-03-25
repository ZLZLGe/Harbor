from pathlib import Path
import re
import subprocess

WORKSPACE = Path("/workspace")


def read_text(relative_path: str) -> str:
    return (WORKSPACE / relative_path).read_text()


def test_required_files_use_jakarta_namespaces():
    expected_packages = {
        "src/main/java/com/example/invoice/domain/InvoiceRecord.java": "jakarta.persistence",
        "src/main/java/com/example/invoice/web/CreateInvoiceRequest.java": "jakarta.validation",
        "src/main/java/com/example/invoice/web/AuditTrailFilter.java": "jakarta.servlet",
        "src/test/java/com/example/invoice/support/CapturingFilterChain.java": "jakarta.servlet",
    }

    for relative_path, package_name in expected_packages.items():
        content = read_text(relative_path)
        assert package_name in content, f"{relative_path} should import {package_name}"


def test_no_legacy_javax_namespaces_remain():
    legacy_pattern = re.compile(r"\bjavax\.(persistence|validation|servlet)\b")
    for java_file in WORKSPACE.rglob("*.java"):
        assert legacy_pattern.search(java_file.read_text()) is None, f"legacy namespace remains in {java_file}"


def test_audit_filter_contract_is_preserved():
    content = read_text("src/main/java/com/example/invoice/web/AuditTrailFilter.java")

    assert '"X-Actor"' in content
    assert '"anonymous"' in content
    assert '"audit.actor"' in content
    assert '"X-Audit-Trace"' in content


def test_maven_tests_pass():
    result = subprocess.run(
        ["mvn", "test", "-q"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
