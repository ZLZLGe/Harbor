from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path(os.environ.get("CONTENT_REVIEW_ACCESS_LOG", "/var/log/content-review/access.log"))
PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""
AGENT_LOG = Path(os.environ.get("AGENT_LOG_PATH", "/logs/agent/codex.txt"))
SOURCE_ROOT = Path(os.environ.get("SOURCE_BUNDLE_ROOT", "/root/workspace/source_bundle"))
SERVICE_ROOT = Path(os.environ.get("CONTENT_REVIEW_SERVICE_ROOT", "/services/content-review"))
SOURCE_HASH_PATH = Path(os.environ.get("SOURCE_BUNDLE_HASH_PATH", "/opt/source-bundle.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("CONTENT_REVIEW_SERVICE_HASH_PATH", "/opt/content-review-service.sha256"))
SKILL_HASH_PATH = Path(os.environ.get("CONTENT_SKILLS_HASH_PATH", "/opt/content-skills.sha256"))
SKILL_ROOT = Path(os.environ.get("CODEX_SKILLS_ROOT", "/root/.codex/skills"))
HEALTH_URL = os.environ.get("CONTENT_REVIEW_HEALTH_URL", "http://127.0.0.1:8147/health")
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/root/output"))
BOUND_SKILL_MD_PATH = Path(os.environ.get("BOUND_SKILL_MD_PATH", "/logs/agent/skills/content-engine/SKILL.md"))


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
        client = record.get("client", "")
        if client.startswith("verifier-"):
            continue
        records.append(record)
    return records


def test_solver_used_review_service_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier review-service traffic was recorded"
    paths = {record["path"] for record in records}
    assert "/api/index" in paths, "Solver did not query the source index"
    assert "/api/constraints" in paths, "Solver did not query campaign constraints"

    source_index = json.loads((SOURCE_ROOT / "source_index.json").read_text(encoding="utf-8"))
    for doc in source_index["docs"]:
        path = f"/api/document/{doc['doc_id']}"
        assert path in paths, f"Solver did not inspect document {doc['doc_id']}"


def test_inputs_hidden_service_and_skill_were_not_modified() -> None:
    current_inputs = subprocess.check_output(
        f"find {SOURCE_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_inputs = SOURCE_HASH_PATH.read_text(encoding="utf-8")
    assert current_inputs == expected_inputs, "Source bundle files were modified"

    current_service = subprocess.check_output(
        f"find {SERVICE_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_service = SERVICE_HASH_PATH.read_text(encoding="utf-8")
    assert current_service == expected_service, "Hidden review service files were modified"

    current_skills = subprocess.check_output(
        f"find {SKILL_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum || true",
        shell=True,
        text=True,
    )
    expected_skills = SKILL_HASH_PATH.read_text(encoding="utf-8")
    assert current_skills == expected_skills, "Bundled skills were modified"


def test_service_still_healthy() -> None:
    req = urllib.request.Request(HEALTH_URL, headers={"X-Client": "verifier-health"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "content-review"


def test_outputs_do_not_reference_tests_or_placeholders() -> None:
    for path in [
        OUTPUT_ROOT / "campaign_summary.md",
        OUTPUT_ROOT / "x_thread.md",
        OUTPUT_ROOT / "linkedin_post.md",
        OUTPUT_ROOT / "newsletter_draft.md",
        OUTPUT_ROOT / "source_map.json",
        OUTPUT_ROOT / "publish_gaps.json",
    ]:
        text = path.read_text(encoding="utf-8").lower()
        assert "placeholder" not in text
        assert "todo" not in text
        assert "verifier" not in text
        assert "/tests" not in text


def test_bound_workflow_was_consulted_when_skill_is_present() -> None:
    if not BOUND_SKILL_MD_PATH.exists() or not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    assert str(BOUND_SKILL_MD_PATH) in text, "Solver did not consult the bundled content-engine workflow"


def test_hidden_service_implementation_was_not_inspected() -> None:
    if not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    forbidden_paths = [
        "/services/content-review/server.py",
        "/opt/content-task-environment/hidden-service-src",
        "environment/hidden-service-src",
    ]
    for path in forbidden_paths:
        assert path not in text, f"Solver inspected hidden review-service implementation: {path}"
