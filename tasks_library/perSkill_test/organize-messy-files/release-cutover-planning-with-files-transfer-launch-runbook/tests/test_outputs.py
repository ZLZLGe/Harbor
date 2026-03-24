import os
import re
from pathlib import Path

TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
RELEASE_ROOT = Path(os.environ.get("RELEASE_WORKSPACE", str(TASK_ROOT / "release_workspace")))
OUTPUT_PATH = TASK_ROOT / "plans" / "cutover_runbook.md"

EXPECTED_SUMMARY_TERMS = [
    "2026.04.08-rc2",
    "2026-04-08 21:00-22:15 UTC",
    "checkout-api",
    "customer-portal",
    "billing-worker",
    "ledger_dual_write",
    "express_wallet",
]

OWNER_KEYWORDS = {
    "Mara Singh": ["release manager", "bridge", "go/no-go", "reopen"],
    "Devon Hale": ["banner", "queue", "traffic"],
    "Priya Natarajan": ["billing-worker", "snapshot", "migration"],
    "Linh Tran": ["deploy", "flag", "application"],
    "Omar Ruiz": ["smoke", "validation", "sign-off", "qa"],
}

EXPECTED_ROW_OWNERS = [
    "Mara Singh",
    "Devon Hale",
    "Priya Natarajan",
    "Priya Natarajan",
    "Linh Tran",
    "Linh Tran",
    "Omar Ruiz",
    "Mara Singh",
]

STEP_TERM_GROUPS = {
    "1": [["go/no-go", "go / no-go", "go no-go"], ["approval", "blocker", "CHG-902", "P0", "P1"]],
    "2": [["banner"], ["queue", "pending_checkout_jobs", "pending jobs"]],
    "3": [["billing-worker"], ["snapshot", "release_cutover_pre_20260408"]],
    "4": [["2026_04_08_add_cutover_columns.sql", "migration"], ["failed_batches", "ledger_backfill_lag", "8 minutes"]],
    "5": [["checkout-api"], ["customer-portal"]],
    "6": [["ledger_dual_write"], ["express_wallet"]],
    "7": [["smoke", "validation"], ["RL-219", "RL-244", "guest_checkout", "refund_lookup"]],
    "8": [["reopen", "restore traffic", "restore customer traffic"], ["error_rate", "p95_checkout", "15 minutes"]],
}

STEP_EVIDENCE_HINTS = {
    "1": ["meetings/go_no_go_notes.md", "qa/defect_register.csv", "product/release_scope.md"],
    "2": ["product/release_scope.md", "operations/monitoring_thresholds.md"],
    "3": ["migration/cutover_plan.md", "meetings/go_no_go_notes.md"],
    "4": ["migration/cutover_plan.md", "operations/monitoring_thresholds.md"],
    "5": ["product/release_scope.md", "meetings/go_no_go_notes.md"],
    "6": ["product/release_scope.md", "qa/defect_register.csv"],
    "7": ["validation/smoke_matrix.csv", "qa/defect_register.csv"],
    "8": ["operations/monitoring_thresholds.md", "meetings/go_no_go_notes.md"],
}

REQUIRED_VALIDATION_CHECKS = [
    "guest_checkout",
    "saved_card_checkout",
    "refund_lookup",
    "invoice_download",
]

ROLLBACK_TERM_GROUPS = [
    ["approval", "go/no-go", "blocker", "CHG-902"],
    ["failed_batches", "8 minutes", "migration"],
    ["RL-219", "RL-244", "smoke"],
    ["error_rate > 3%", "error_rate", "5 minutes"],
]

FINDINGS_TERMS = [
    "2026.04.08-rc2",
    "failed_batches",
    "RL-219",
    "RL-244",
    "error_rate",
    "p95_checkout",
    "express_wallet",
]


def read_text(path: Path) -> str:
    assert path.is_file(), f"Missing file: {path}"
    return path.read_text(encoding="utf-8")


def section_slice(text: str, heading: str) -> str:
    pattern = rf"^{re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    assert match, f"Missing section: {heading}"
    return match.group(1).strip()


def parse_markdown_table(section: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    assert len(lines) >= 3, "Execution sequence must contain a Markdown table."

    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    assert header == [
        "Step",
        "Window",
        "Owner",
        "Dependencies",
        "Action",
        "Verification",
        "Rollback Trigger",
        "Evidence",
    ]

    rows: list[dict[str, str]] = []
    for raw_line in lines[2:]:
        cells = [cell.strip() for cell in raw_line.strip("|").split("|")]
        assert len(cells) == len(header), f"Malformed table row: {raw_line}"
        rows.append(dict(zip(header, cells)))
    return rows


def line_with_name(section: str, name: str) -> str:
    for line in section.splitlines():
        if name.lower() in line.lower():
            return line.lower()
    return ""


def contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def test_release_assets_exist():
    expected_files = [
        RELEASE_ROOT / "product" / "release_scope.md",
        RELEASE_ROOT / "migration" / "cutover_plan.md",
        RELEASE_ROOT / "qa" / "defect_register.csv",
        RELEASE_ROOT / "rollback" / "rollback_snippets.sh",
        RELEASE_ROOT / "meetings" / "go_no_go_notes.md",
        RELEASE_ROOT / "validation" / "smoke_matrix.csv",
        RELEASE_ROOT / "operations" / "owner_roster.csv",
        RELEASE_ROOT / "operations" / "monitoring_thresholds.md",
    ]
    for path in expected_files:
        assert path.is_file(), f"Missing release evidence file: {path}"


def test_runbook_structure_and_summary():
    text = read_text(OUTPUT_PATH)
    assert text.startswith("# Release Cutover Runbook")

    for heading in [
        "## Release Summary",
        "## Owner Map",
        "## Execution Sequence",
        "## Validation Gates",
        "## Rollback Triggers",
    ]:
        assert heading in text

    summary = section_slice(text, "## Release Summary")
    for term in EXPECTED_SUMMARY_TERMS:
        assert term in summary, f"Summary should mention {term!r}"


def test_owner_map_lists_all_named_owners_with_responsibilities():
    text = read_text(OUTPUT_PATH)
    owner_map = section_slice(text, "## Owner Map")

    assert len(nonempty_lines(owner_map)) >= 5
    for owner, keywords in OWNER_KEYWORDS.items():
        assert owner in owner_map, f"Owner map should include {owner}"
        owner_line = line_with_name(owner_map, owner)
        assert owner_line, f"Owner map should list {owner} on a dedicated line or row"
        assert contains_any(owner_line, keywords), f"Owner line for {owner} should describe responsibilities"


def test_execution_sequence_table_uses_bridge_order_and_concrete_evidence():
    text = read_text(OUTPUT_PATH)
    sequence = section_slice(text, "## Execution Sequence")
    rows = parse_markdown_table(sequence)

    assert len(rows) == 8, "Execution sequence must contain exactly 8 data rows."
    assert [row["Step"] for row in rows] == [str(index) for index in range(1, 9)]
    assert [row["Owner"] for row in rows] == EXPECTED_ROW_OWNERS

    for row in rows:
        for column in [
            "Window",
            "Owner",
            "Dependencies",
            "Action",
            "Verification",
            "Rollback Trigger",
            "Evidence",
        ]:
            assert row[column], f"Step {row['Step']} must fill the {column} column."

        row_text = " ".join(row.values())
        for terms in STEP_TERM_GROUPS[row["Step"]]:
            assert contains_any(row_text, terms), f"Step {row['Step']} is missing a core cutover fact."

        assert contains_any(row["Evidence"], STEP_EVIDENCE_HINTS[row["Step"]]), (
            f"Step {row['Step']} should cite evidence files tied to that phase."
        )


def test_validation_and_rollback_sections_cover_release_critical_items():
    text = read_text(OUTPUT_PATH)

    validation = section_slice(text, "## Validation Gates")
    validation_bullets = [line for line in validation.splitlines() if line.startswith("- ")]
    assert len(validation_bullets) >= 4
    for check_id in REQUIRED_VALIDATION_CHECKS:
        assert check_id in validation, f"Validation section should cover {check_id}"

    rollback = section_slice(text, "## Rollback Triggers")
    rollback_bullets = [line for line in rollback.splitlines() if line.startswith("- ")]
    assert len(rollback_bullets) >= 4
    for terms in ROLLBACK_TERM_GROUPS:
        assert contains_any(rollback, terms), "Rollback section is missing a required stop or reverse condition."


def test_working_notes_exist_and_capture_working_state():
    task_plan = read_text(TASK_ROOT / "task_plan.md")
    findings = read_text(TASK_ROOT / "findings.md")
    progress = read_text(TASK_ROOT / "progress.md")

    assert len(nonempty_lines(task_plan)) >= 3
    assert contains_any(task_plan, ["runbook", "cutover", "sequence", "checklist"])

    assert len(nonempty_lines(findings)) >= 3
    findings_hits = sum(1 for term in FINDINGS_TERMS if term in findings)
    assert findings_hits >= 2, "Findings should record concrete facts or thresholds from the evidence."

    assert len(nonempty_lines(progress)) >= 2
    assert contains_any(progress, ["cutover_runbook.md", "plans/cutover_runbook.md"])
