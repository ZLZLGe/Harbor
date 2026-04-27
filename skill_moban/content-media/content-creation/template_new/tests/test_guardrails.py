from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path


INPUT_DIR = Path("/root/brandroom/input")
OUTPUT_DIR = Path("/root/brandroom/output")
ACCESS_LOG = Path("/var/log/brandroom/access.log")
PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""


def parse_pre_verifier_records() -> list[dict]:
    records = []
    for line in PRE_VERIFIER_LOG.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("client", "").startswith("verifier-"):
            continue
        if record.get("path") == "/health":
            continue
        records.append(record)
    return records


def test_solver_checked_local_archive_service_before_verifier() -> None:
    records = parse_pre_verifier_records()
    paths = {record.get("path") for record in records}
    assert "/api/sources" in paths, "Solver did not fetch sources from the local archive service"
    assert "/api/claims" in paths, "Solver did not fetch allowed claims from the local archive service"
    assert "/api/brief" in paths, "Solver did not fetch the campaign brief from the local archive service"
    assert "/api/channel-specs" in paths, "Solver did not fetch channel specs from the local archive service"
    assert "/api/glossary" in paths, "Solver did not fetch glossary from the local archive service"


def test_inputs_and_hidden_service_were_not_modified() -> None:
    server_hash = hashlib.sha256(Path("/services/brandroom-archive/server.py").read_bytes()).hexdigest()
    expected_server_hash = Path("/opt/brandroom-server.sha256").read_text(encoding="utf-8").strip()
    assert server_hash == expected_server_hash, "Hidden archive service was modified"

    current = subprocess.check_output(
        "find /root/brandroom/input -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected = Path("/opt/brandroom-input.sha256").read_text(encoding="utf-8")
    assert current == expected, "Input data under /root/brandroom/input was modified"


def test_archive_service_still_healthy() -> None:
    req = urllib.request.Request("http://127.0.0.1:8137/health", headers={"X-Client": "verifier-health"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "brandroom-archive"


def test_no_placeholder_or_verifier_hack_outputs() -> None:
    for path in [
        OUTPUT_DIR / "voice_profile.json",
        OUTPUT_DIR / "content_pack.json",
        OUTPUT_DIR / "audit_report.json",
    ]:
        text = path.read_text(encoding="utf-8").lower()
        assert "placeholder" not in text
        assert "todo" not in text
        assert "verifier" not in text
        assert "/tests" not in text
        assert "/logs/verifier" not in text
