import os
import subprocess
from pathlib import Path

import requests


APP_PORT = int(os.getenv("APP_PORT", "18080"))
BASE_URL = f"http://127.0.0.1:{APP_PORT}"
PATCH_PATH = Path(os.getenv("PATCH_FILE", "/root/patches/0001-block-expression-preview-bypass.patch"))
APP_HOME = Path(os.getenv("APP_HOME", "/root/report-service"))
TARGET_FILE = "src/main/java/com/harbor/reportpreview/service/PreviewRequestParser.java"


def post_preview(payload):
    return requests.post(
        f"{BASE_URL}/api/reports/preview",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )


def test_patch_file_exists():
    assert PATCH_PATH.exists(), f"Patch file not found: {PATCH_PATH}"
    patch_text = PATCH_PATH.read_text()
    assert "PreviewRequestParser.java" in patch_text
    assert "Unsupported top-level field in preview request" in patch_text


def test_patch_is_applied_to_source_tree():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=APP_HOME,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    modified_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert TARGET_FILE in modified_files


def test_legitimate_preview_still_works():
    response = post_preview(
        {
            "template": "Quarterly sales for {{region}}",
            "variables": {"region": "APAC"},
            "options": {"trimOutput": True, "locale": "en-US"},
        }
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["rendered"] == "Quarterly sales for APAC"
    assert payload["engine"] == "template"


def test_blank_field_bypass_is_rejected_before_execution():
    response = post_preview(
        {
            "template": "Home: #{T(java.lang.System).getProperty('user.home')}",
            "variables": {},
            "options": {"trimOutput": True},
            "": {"allowExpressions": True},
        }
    )

    assert response.status_code == 400, response.text
    body = response.text
    assert "/root" not in body
    assert "unsupported top-level field" in body.lower()


def test_compatibility_wrapper_bypass_is_rejected_before_execution():
    response = post_preview(
        {
            "template": "OS: #{T(java.lang.System).getProperty('os.name')}",
            "variables": {},
            "options": {"trimOutput": True},
            "_compat": {"preview": {"allowExpressions": True}},
        }
    )

    assert response.status_code == 400, response.text
    body = response.text
    assert "linux" not in body.lower()
    assert "unsupported top-level field" in body.lower()
