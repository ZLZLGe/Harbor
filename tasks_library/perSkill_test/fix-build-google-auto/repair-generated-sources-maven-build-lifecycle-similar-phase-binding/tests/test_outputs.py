from functools import lru_cache
from pathlib import Path
import subprocess


PROJECT_DIR = Path("/workspace/build-metadata-service")
GENERATED_FILE = PROJECT_DIR / "target/generated-sources/build-meta/com/acme/build/BuildMetadata.java"


@lru_cache(maxsize=1)
def run_verify():
    result = subprocess.run(
        ["mvn", "verify"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    return result


def test_mvn_verify_succeeds():
    result = run_verify()
    assert result.returncode == 0, "expected `mvn verify` to succeed"


def test_generated_metadata_contract():
    result = run_verify()
    assert result.returncode == 0, "build must succeed before checking generated output"
    assert GENERATED_FILE.exists(), f"missing generated file: {GENERATED_FILE}"

    content = GENERATED_FILE.read_text()

    assert "package com.acme.build;" in content
    assert "public final class BuildMetadata" in content
    assert 'public static final String APP_NAME = "LedgerSync";' in content
    assert 'public static final String DEPLOYMENT_TRACK = "canary";' in content
    assert 'public static final String BUILD_REVISION = "2026.03.25";' in content
    assert "public static String describe()" in content
