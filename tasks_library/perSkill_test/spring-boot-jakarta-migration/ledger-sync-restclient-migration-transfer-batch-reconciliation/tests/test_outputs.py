from pathlib import Path
import subprocess

WORKSPACE = Path("/workspace")
TARGET = WORKSPACE / "src/main/java/com/example/reconciliation/client/LedgerSyncClient.java"


def read_target() -> str:
    assert TARGET.exists(), f"Missing target file: {TARGET}"
    return TARGET.read_text()


def test_uses_restclient_not_resttemplate():
    content = read_target()
    assert "RestClient" in content, "LedgerSyncClient must use RestClient"
    assert "RestTemplate" not in content, "RestTemplate should be removed from LedgerSyncClient"


def test_preserves_generic_page_mapping_and_cursor_logic():
    content = read_target()
    assert "ParameterizedTypeReference<PageEnvelope<LedgerEntry>>" in content, "Paged ledger fetch should keep the generic response mapping"
    assert 'queryParam("limit", limit)' in content, "fetchEntries should keep the limit query parameter"
    assert 'queryParam("ledgerDate", ledgerDate)' in content, "fetchEntries should keep the ledgerDate query parameter"
    assert "if (cursor != null && !cursor.isBlank())" in content, "Cursor should only be sent when present"
    assert 'queryParam("cursor", cursor)' in content, "fetchEntries should append the cursor query parameter"


def test_posts_confirmation_batch_with_fluent_client():
    content = read_target()
    assert ".post()" in content, "Confirmation submission should use a POST RestClient call"
    assert '.uri("/ledger/entries/confirmations")' in content, "submitConfirmations should keep the confirmation endpoint"
    assert ".body(batch)" in content, "submitConfirmations should send the batch payload"


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
