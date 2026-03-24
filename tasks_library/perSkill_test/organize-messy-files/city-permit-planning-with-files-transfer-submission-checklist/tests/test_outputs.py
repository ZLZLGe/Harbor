import csv
import os
from pathlib import Path

TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
PERMIT_ROOT = Path(os.environ.get("PERMIT_ROOT", str(TASK_ROOT / "permit_workspace")))
OUTPUT_PATH = TASK_ROOT / "deliverables" / "permit_submission_checklist.csv"

EXPECTED_ROWS = {
    "accessibility_ramp_details": {
        "status": "satisfied",
        "blocking_issue": "no",
        "evidence_refs": [
            "permit_workspace/drawings/site_plan.svg",
            "permit_workspace/drawings/accessibility_ramp_schedule.csv",
        ],
        "note_terms": ["1:12", "60x60", "handrails"],
    },
    "neighbor_notification_affidavit": {
        "status": "missing",
        "blocking_issue": "yes",
        "evidence_refs": [
            "permit_workspace/rules/city_checklist_excerpt.md",
            "permit_workspace/emails/plan_review_followup.md",
        ],
        "note_terms": ["alley", "no affidavit"],
    },
    "owner_authorization": {
        "status": "satisfied",
        "blocking_issue": "no",
        "evidence_refs": [
            "permit_workspace/forms/permit_application.csv",
            "permit_workspace/forms/owner_authorization.txt",
        ],
        "note_terms": ["signed", "authorization"],
    },
    "parcel_identifier_consistency": {
        "status": "conflict",
        "blocking_issue": "yes",
        "evidence_refs": [
            "permit_workspace/forms/permit_application.csv",
            "permit_workspace/drawings/site_plan.svg",
            "permit_workspace/emails/plan_review_followup.md",
        ],
        "note_terms": ["417-19-008", "417-19-006", "conflict"],
    },
    "permit_application_signature": {
        "status": "satisfied",
        "blocking_issue": "no",
        "evidence_refs": ["permit_workspace/forms/permit_application.csv"],
        "note_terms": ["applicant_signed=yes"],
    },
    "project_valuation_support": {
        "status": "satisfied",
        "blocking_issue": "no",
        "evidence_refs": [
            "permit_workspace/forms/permit_application.csv",
            "permit_workspace/forms/project_cost_breakdown.csv",
            "permit_workspace/quotes/general_contractor_quote.txt",
            "permit_workspace/quotes/traffic_control_quote.txt",
        ],
        "note_terms": ["172400", "12600", "185000"],
    },
    "stormwater_worksheet": {
        "status": "missing",
        "blocking_issue": "yes",
        "evidence_refs": [
            "permit_workspace/forms/permit_application.csv",
            "permit_workspace/rules/city_checklist_excerpt.md",
            "permit_workspace/emails/plan_review_followup.md",
        ],
        "note_terms": ["960", "stormwater", "not included"],
    },
    "utility_service_alignment": {
        "status": "conflict",
        "blocking_issue": "yes",
        "evidence_refs": [
            "permit_workspace/forms/permit_application.csv",
            "permit_workspace/drawings/electrical_riser.svg",
            "permit_workspace/emails/plan_review_followup.md",
        ],
        "note_terms": ["400A", "320A", "inconsistent"],
    },
}

EXPECTED_COLUMNS = [
    "item_id",
    "requirement",
    "status",
    "evidence",
    "blocking_issue",
    "notes",
]


def read_rows():
    assert OUTPUT_PATH.is_file(), f"Missing checklist: {OUTPUT_PATH}"
    with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == EXPECTED_COLUMNS
        rows = list(reader)
    return rows


def test_assets_exist():
    expected_files = [
        PERMIT_ROOT / "rules" / "city_checklist_excerpt.md",
        PERMIT_ROOT / "forms" / "permit_application.csv",
        PERMIT_ROOT / "forms" / "owner_authorization.txt",
        PERMIT_ROOT / "forms" / "project_cost_breakdown.csv",
        PERMIT_ROOT / "emails" / "plan_review_followup.md",
        PERMIT_ROOT / "drawings" / "site_plan.svg",
        PERMIT_ROOT / "drawings" / "electrical_riser.svg",
        PERMIT_ROOT / "drawings" / "accessibility_ramp_schedule.csv",
        PERMIT_ROOT / "quotes" / "general_contractor_quote.txt",
        PERMIT_ROOT / "quotes" / "traffic_control_quote.txt",
    ]
    for path in expected_files:
        assert path.is_file(), f"Missing permit evidence file: {path}"


def test_checklist_shape_and_order():
    rows = read_rows()
    assert len(rows) == 8
    assert [row["item_id"] for row in rows] == sorted(EXPECTED_ROWS)


def test_checklist_statuses_blockers_and_evidence():
    rows = {row["item_id"]: row for row in read_rows()}
    assert set(rows) == set(EXPECTED_ROWS)

    blocker_ids = []
    for item_id, expected in EXPECTED_ROWS.items():
        row = rows[item_id]
        assert row["status"] == expected["status"]
        assert row["blocking_issue"] == expected["blocking_issue"]
        assert row["requirement"].strip()
        assert row["notes"].strip()

        if row["blocking_issue"] == "yes":
            blocker_ids.append(item_id)

        for evidence_ref in expected["evidence_refs"]:
            assert evidence_ref in row["evidence"], f"{item_id} should cite {evidence_ref}"

        notes_lower = row["notes"].lower()
        for term in expected["note_terms"]:
            assert term.lower() in notes_lower, f"{item_id} notes should mention {term!r}"

    assert blocker_ids == [
        "neighbor_notification_affidavit",
        "parcel_identifier_consistency",
        "stormwater_worksheet",
        "utility_service_alignment",
    ]


def test_working_notes_exist_and_capture_key_findings():
    task_plan = (TASK_ROOT / "task_plan.md").read_text(encoding="utf-8")
    findings = (TASK_ROOT / "findings.md").read_text(encoding="utf-8")
    progress = (TASK_ROOT / "progress.md").read_text(encoding="utf-8")

    assert "stormwater_worksheet" in task_plan
    assert "utility_service_alignment" in task_plan
    assert "417-19-006" in findings
    assert "320A" in findings
    assert "185000" in findings
    assert "permit_submission_checklist.csv" in progress
