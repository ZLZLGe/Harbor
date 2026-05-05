from __future__ import annotations

import json
import os
from pathlib import Path


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
TARGET_PROFILE = json.loads((DATA_DIR / "engagement" / "target_profile.json").read_text(encoding="utf-8"))
ALLOWED_LABELS = {item["label"] for item in TARGET_PROFILE["allowed_identities"]}
REQUIRED_CATEGORIES = {"authorization", "data-exposure", "rate-limiting", "error-handling"}
REQUIRED_COVERAGE_KEYS = {
    "endpoint_inventory_count",
    "discovery_complete",
    "authn_checked",
    "authorization_checked",
    "rate_limit_checked",
    "error_handling_checked",
}


def load_findings() -> dict:
    return json.loads((OUTPUT_DIR / "security_findings.json").read_text(encoding="utf-8"))


def load_repro() -> str:
    return (OUTPUT_DIR / "reproduction.md").read_text(encoding="utf-8")


def resolve_evidence(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = OUTPUT_DIR / path
    return path


def files_for_category(payload: dict, category: str) -> list[Path]:
    for finding in payload["findings"]:
        if finding["category"] == category:
            return [resolve_evidence(item) for item in finding["evidence_files"]]
    raise AssertionError(f"Missing finding for category: {category}")


def combined_text(paths: list[Path]) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def test_required_output_files_exist() -> None:
    assert (OUTPUT_DIR / "security_findings.json").exists(), "Missing security_findings.json"
    assert (OUTPUT_DIR / "reproduction.md").exists(), "Missing reproduction.md"
    assert (OUTPUT_DIR / "evidence").is_dir(), "Missing evidence directory"
    names = sorted(item.name for item in OUTPUT_DIR.iterdir())
    assert names == ["evidence", "reproduction.md", "security_findings.json"], "Unexpected files were written to /root/output"


def test_security_findings_schema_and_categories() -> None:
    payload = load_findings()
    assert payload["engagement_id"] == TARGET_PROFILE["engagement_id"]
    assert payload["target_base_url"] == TARGET_PROFILE["target_base_url"]

    tested = payload["tested_identities"]
    assert isinstance(tested, list) and len(tested) == 3
    assert {item["label"] for item in tested} == ALLOWED_LABELS
    for item in tested:
        assert item["tenant"]
        assert item["role"]

    coverage = payload["coverage"]
    assert REQUIRED_COVERAGE_KEYS.issubset(coverage.keys())
    assert coverage["endpoint_inventory_count"] >= 4
    for key in REQUIRED_COVERAGE_KEYS - {"endpoint_inventory_count"}:
        assert coverage[key] is True, f"Coverage flag {key} must be true"

    findings = payload["findings"]
    assert isinstance(findings, list) and len(findings) == 4
    assert {item["category"] for item in findings} == REQUIRED_CATEGORIES

    for finding in findings:
        assert finding["id"], "Each finding needs a non-empty id"
        assert finding["severity"] in {"critical", "high", "medium", "low"}
        assert finding["endpoint"], "Each finding needs an endpoint"
        assert finding["affected_identity"] in ALLOWED_LABELS
        assert finding["summary"].strip()
        assert finding["impact"].strip()
        assert finding["recommendation"].strip()
        assert finding["evidence_files"], f"Finding {finding['id']} must reference evidence files"
        for item in finding["evidence_files"]:
            path = resolve_evidence(item)
            assert path.exists(), f"Evidence file is missing: {item}"
            assert path.is_file(), f"Evidence path must be a file: {item}"


def test_reproduction_sections_and_cross_references() -> None:
    payload = load_findings()
    text = load_repro()

    expected_sections = [
        "# OrderHub API Security Review",
        "## Scope",
        "## Coverage",
        "## Findings",
        "## Reproduction Steps",
        "## Suggested Follow-up",
    ]
    last_index = -1
    for section in expected_sections:
        idx = text.find(section)
        assert idx >= 0, f"Missing section: {section}"
        assert idx > last_index, f"Section order is wrong around {section}"
        last_index = idx

    assert "| Endpoint | Identity | Observation |" in text, "Coverage table is missing"
    for finding in payload["findings"]:
        assert finding["id"] in text, f"reproduction.md does not mention finding {finding['id']}"
        for item in finding["evidence_files"]:
            assert Path(item).name in text, f"reproduction.md does not mention evidence file {item}"


def test_evidence_contents_show_confirmed_issues() -> None:
    payload = load_findings()

    auth_text = combined_text(files_for_category(payload, "authorization"))
    assert "10278" in auth_text or "10643" in auth_text, "Authorization evidence does not include a cross-tenant order id"
    assert "tenant_alpha_analyst" in auth_text or "tenant_beta_analyst" in auth_text, "Authorization evidence does not show the caller identity"
    assert "\"tenant_id\": \"beta\"" in auth_text or "\"tenant_id\": \"alpha\"" in auth_text, "Authorization evidence does not show cross-tenant data"

    export_text = combined_text(files_for_category(payload, "data-exposure"))
    assert "all_tenants" in export_text, "Export evidence does not show the all_tenants scope"
    assert "tenants_included" in export_text, "Export evidence does not include the tenant list"
    assert "contact_name" in export_text, "Export evidence does not show exposed contact data"

    rate_text = combined_text(files_for_category(payload, "rate-limiting"))
    sequence_lines = [line for line in rate_text.splitlines() if line.strip()]
    assert len(sequence_lines) >= 6, "Rate-limit evidence must include a burst sequence"
    assert "429" not in rate_text, "Rate-limit evidence unexpectedly shows enforcement"
    assert "remaining=-" in rate_text.lower() or "remaining=0" in rate_text.lower(), "Rate-limit evidence does not show exhausted headers"

    error_text = combined_text(files_for_category(payload, "error-handling"))
    assert "Traceback" in error_text, "Error-handling evidence must show a traceback"
    assert "SELECT order_id, ship_country FROM orders ORDER BY" in error_text, "Error-handling evidence must show the disclosed SQL"
