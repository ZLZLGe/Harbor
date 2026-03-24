import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path("/workspace")
if not WORKSPACE.exists():
    WORKSPACE = REPO_ROOT / "environment/workspace"
TARGET = WORKSPACE / "src/main/java/com/example/reporting/client/ArchiveExportClient.java"


def read_target() -> str:
    assert TARGET.exists(), f"Missing target file: {TARGET}"
    return TARGET.read_text()


def test_uses_restclient_not_resttemplate():
    content = read_target()
    assert "RestClient" in content, "ArchiveExportClient must use RestClient"
    assert "RestTemplate" not in content, "RestTemplate should be removed from ArchiveExportClient"


def test_keeps_archive_endpoints():
    content = read_target()
    assert '"/archive/exports/{exportId}/csv"' in content, "CSV endpoint should remain unchanged"
    assert '"/archive/exports/{exportId}/pdf"' in content, "PDF endpoint should remain unchanged"


def test_keeps_confirmation_endpoint():
    content = read_target()
    assert '"/archive/import-confirmations"' in content, "Import confirmation endpoint should remain unchanged"


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
