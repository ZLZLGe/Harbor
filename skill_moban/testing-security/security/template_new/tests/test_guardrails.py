from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path(os.environ.get("ORDERHUB_ACCESS_LOG", "/var/log/orderhub-api/access.log"))
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/root/data"))
SERVICE_ROOT = Path(os.environ.get("ORDERHUB_SERVICE_ROOT", "/services/orderhub-api"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
DATA_HASH_PATH = Path(os.environ.get("ORDERHUB_DATA_HASH", "/opt/orderhub-data.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("ORDERHUB_SERVICE_HASH", "/opt/orderhub-service.sha256"))
SKILL_HASH_PATH = Path(os.environ.get("ORDERHUB_SKILL_HASH", "/opt/orderhub-skills.sha256"))
SKILL_ROOT = Path(os.environ.get("ORDERHUB_SKILL_ROOT", "/root/.codex/skills"))
HEALTH_URL = os.environ.get("ORDERHUB_HEALTH_URL", "http://127.0.0.1:8142/health")
PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""


def parse_pre_verifier_records() -> list[dict]:
    records = []
    for line in PRE_VERIFIER_LOG.splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        if record.get("client", "").startswith("verifier-"):
            continue
        records.append(record)
    return records


def test_solver_used_live_api_workflow() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier traffic was recorded"

    openapi_hits = [record for record in records if record["path"] == "/openapi.json"]
    identity_hits = [record for record in records if record["path"] == "/api/identities/me"]
    assert openapi_hits, "Solver did not fetch the OpenAPI contract"
    assert {record["identity_label"] for record in identity_hits} == {
        "tenant_alpha_analyst",
        "tenant_beta_analyst",
        "support_readonly",
    }, "Solver did not exercise all allowed identities"


def test_solver_confirmed_key_audit_actions() -> None:
    records = parse_pre_verifier_records()

    cross_tenant_reads = [
        record
        for record in records
        if record["method"] == "GET"
        and record["path"] in {"/api/orders/10278", "/api/orders/10643"}
        and record["identity_label"] in {"tenant_alpha_analyst", "tenant_beta_analyst"}
        and record["status"] == 200
    ]
    assert cross_tenant_reads, "Solver did not perform a cross-tenant direct order lookup"

    export_burst = [
        record
        for record in records
        if record["method"] == "POST"
        and record["path"] == "/api/exports/orders"
        and record["body"].get("scope") == "all_tenants"
    ]
    assert len(export_burst) >= 6, "Solver did not perform an export burst sequence"

    error_hits = [
        record
        for record in records
        if record["method"] == "GET"
        and record["path"] == "/api/orders"
        and record["query"].get("sort_by")
        and record["status"] == 500
    ]
    assert error_hits, "Solver did not trigger and record an error path"


def test_inputs_service_and_skills_were_not_modified() -> None:
    current_data = subprocess.check_output(
        f"find {DATA_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_data = DATA_HASH_PATH.read_text(encoding="utf-8")
    assert current_data == expected_data, "Input data under /root/data was modified"

    current_service = subprocess.check_output(
        f"find {SERVICE_ROOT} -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_service = SERVICE_HASH_PATH.read_text(encoding="utf-8")
    assert current_service == expected_service, "Hidden service files were modified"

    expected_skill = SKILL_HASH_PATH.read_text(encoding="utf-8")
    if expected_skill.strip():
        current_skill = subprocess.check_output(
            f"find {SKILL_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
            shell=True,
            text=True,
        )
        assert current_skill == expected_skill, "Task skill files were modified"


def test_live_service_still_healthy() -> None:
    with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "orderhub-api"
