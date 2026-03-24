import os
import re
from pathlib import Path

TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
INCIDENT_ROOT = Path(os.environ.get("INCIDENT_ROOT", str(TASK_ROOT / "incident_workspace")))
REPORT_PATH = TASK_ROOT / "reports" / "outage_postmortem.md"


def read_text(path: Path) -> str:
    assert path.is_file(), f"Missing file: {path}"
    return path.read_text(encoding="utf-8")


def section_slice(text: str, heading: str) -> str:
    pattern = rf"^{re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    assert match, f"Missing section: {heading}"
    return match.group(1).strip()


def test_incident_workspace_assets_exist():
    expected_files = [
        INCIDENT_ROOT / "alerts" / "alerts_export.csv",
        INCIDENT_ROOT / "logs" / "checkout-api.log",
        INCIDENT_ROOT / "logs" / "postgres_pool.log",
        INCIDENT_ROOT / "chat" / "oncall_chat.md",
        INCIDENT_ROOT / "tickets" / "INC-4821.md",
        INCIDENT_ROOT / "tickets" / "CHG-771.md",
        INCIDENT_ROOT / "config" / "checkout.before.env",
        INCIDENT_ROOT / "config" / "checkout.after.env",
    ]
    for path in expected_files:
        assert path.is_file(), f"Missing incident evidence file: {path}"


def test_report_structure_and_required_sections():
    text = read_text(REPORT_PATH)
    assert text.startswith("# Outage Postmortem")

    for heading in [
        "## Executive Summary",
        "## Customer Impact",
        "## Timeline",
        "## Root Cause Hypothesis",
        "## Key Evidence",
        "## Open Questions",
    ]:
        assert heading in text


def test_timeline_contains_ordered_utc_events():
    text = read_text(REPORT_PATH)
    timeline = section_slice(text, "## Timeline")
    rows = [line for line in timeline.splitlines() if line.startswith("| 2026-02-14 ")]
    assert len(rows) >= 6, "Timeline must include at least 6 dated events."

    required_timestamps = [
        "2026-02-14 09:12:18",
        "2026-02-14 09:14:55",
        "2026-02-14 09:16:10",
        "2026-02-14 09:26:40",
        "2026-02-14 09:31:02",
        "2026-02-14 09:39:12",
    ]
    positions = []
    for timestamp in required_timestamps:
        matching = [idx for idx, row in enumerate(rows) if timestamp in row]
        assert matching, f"Timeline is missing timestamp {timestamp}"
        positions.append(matching[0])

    assert positions == sorted(positions), "Timeline timestamps must be in chronological order."
    assert all("`" in row for row in rows), "Each timeline row should cite evidence files."


def test_customer_impact_and_root_cause_content():
    text = read_text(REPORT_PATH)
    customer_impact = section_slice(text, "## Customer Impact")
    assert "/v1/checkout/session" in customer_impact or "checkout" in customer_impact.lower()
    assert "23%" in customer_impact
    assert "09:16" in customer_impact and "09:39" in customer_impact

    hypothesis = section_slice(text, "## Root Cause Hypothesis")
    required_terms = [
        "2026.02.14-rc3",
        "INVOICE_PREFETCH_MODE",
        "sync",
        "PostgreSQL connection pool",
        "db pool exhausted",
        "payments provider",
    ]
    for term in required_terms:
        assert term in hypothesis, f"Root cause hypothesis should mention {term!r}"


def test_key_evidence_and_open_questions():
    text = read_text(REPORT_PATH)
    evidence = section_slice(text, "## Key Evidence")
    evidence_bullets = [line for line in evidence.splitlines() if line.startswith("- ")]
    assert len(evidence_bullets) >= 4

    required_refs = [
        "config/checkout.after.env",
        "tickets/CHG-771.md",
        "logs/checkout-api.log",
        "logs/postgres_pool.log",
        "alerts/alerts_export.csv",
        "chat/oncall_chat.md",
    ]
    for ref in required_refs:
        assert ref in evidence, f"Key evidence should reference {ref}"

    open_questions = section_slice(text, "## Open Questions")
    question_bullets = [line for line in open_questions.splitlines() if line.startswith("- ")]
    assert len(question_bullets) >= 2


def test_working_notes_exist_and_capture_investigation():
    task_plan = read_text(TASK_ROOT / "task_plan.md")
    findings = read_text(TASK_ROOT / "findings.md")
    progress = read_text(TASK_ROOT / "progress.md")

    assert "2026.02.14-rc3" in task_plan
    assert "timeline" in task_plan.lower()
    assert "INVOICE_PREFETCH_MODE=sync" in findings
    assert "DBPoolSaturation" in findings
    assert "outage_postmortem.md" in progress
