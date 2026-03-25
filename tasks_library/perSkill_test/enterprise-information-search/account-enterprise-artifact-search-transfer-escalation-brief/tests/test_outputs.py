import json
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
REQUEST_PATH = Path(os.environ.get("REQUEST_PATH", str(ROOT_DIR / "escalation_request.json")))
OPS_ROOT = Path(os.environ.get("OPS_ROOT", str(ROOT_DIR / "customer_ops")))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", str(ROOT_DIR / "customer_escalation_brief.json")))

EXPECTED_CUSTOMERS = ["CUST-118", "CUST-774"]
EXPECTED_COMMITMENTS = {
    "COM-2401": {
        "summary": "Backfill tenant-local timestamps in audit exports",
        "owner_employee_id": "eid_7f4c1a20",
        "fix_pr_ids": ["PR-1842"],
        "meeting_id": "MTG-ESC-021",
        "demo_url": "https://demo.internal.example.com/byh/audit-export-v2",
        "latest_state": "delivered",
        "latest_message_id": "msg-114",
    },
    "COM-2402": {
        "summary": "Ship editable SSO role mapping preview with named role templates",
        "owner_employee_id": "eid_29b3e710",
        "fix_pr_ids": ["PR-1860"],
        "meeting_id": "MTG-ESC-022",
        "demo_url": "https://demo.internal.example.com/byh/sso-role-mapping-preview",
        "latest_state": "customer_validation",
        "latest_message_id": "msg-123",
    },
    "COM-2403": {
        "summary": "Provide API retry analytics dashboard and weekly screenshot until GA",
        "owner_employee_id": "eid_c91aa2d4",
        "fix_pr_ids": ["PR-1882"],
        "meeting_id": "MTG-ESC-023",
        "demo_url": "https://demo.internal.example.com/byh/retry-analytics-dashboard",
        "latest_state": "preview_shared",
        "latest_message_id": "msg-129",
    },
}
EXCLUDED_COMMITMENTS = {"COM-2404", "COM-2388", "COM-2410"}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_output():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    return load_json(OUTPUT_PATH)


def split_pointer(pointer: str):
    path_part, _, fragment = pointer.partition("#")
    return path_part, fragment


def assert_pointer_exists(pointer: str):
    assert isinstance(pointer, str) and pointer.strip(), f"Invalid pointer: {pointer!r}"
    path_part, fragment = split_pointer(pointer)
    assert path_part.startswith("customer_ops/"), f"Pointer must use a /root-relative customer_ops path: {pointer}"
    full_path = ROOT_DIR / path_part
    assert full_path.exists(), f"Pointer path does not exist: {pointer}"
    assert fragment, f"Pointer must include a record fragment: {pointer}"


def test_inputs_exist():
    assert REQUEST_PATH.exists(), f"Missing request file: {REQUEST_PATH}"
    assert OPS_ROOT.exists(), f"Missing ops root: {OPS_ROOT}"


def test_output_schema_and_values():
    data = load_output()
    assert data["account_id"] == "ACC-042"
    assert data["escalation_id"] == "ESC-2026-017"
    assert data["affected_customer_ids"] == EXPECTED_CUSTOMERS

    commitments = data["commitments"]
    assert isinstance(commitments, list) and commitments, "commitments must be a non-empty list"

    got_ids = [item["commitment_id"] for item in commitments]
    assert got_ids == sorted(EXPECTED_COMMITMENTS.keys())
    assert EXCLUDED_COMMITMENTS.isdisjoint(got_ids), f"Excluded commitments leaked into output: {got_ids}"

    for item in commitments:
        expected = EXPECTED_COMMITMENTS[item["commitment_id"]]
        assert item["summary"] == expected["summary"]
        assert item["owner_employee_id"] == expected["owner_employee_id"]

        fix_prs = item["fix_prs"]
        assert isinstance(fix_prs, list) and fix_prs, "fix_prs must be a non-empty list"
        assert [pr["pr_id"] for pr in fix_prs] == expected["fix_pr_ids"]
        for pr in fix_prs:
            assert_pointer_exists(pr["artifact_pointer"])
            assert split_pointer(pr["artifact_pointer"])[0] == "customer_ops/prs/fix_prs.json"

        meeting_record = item["meeting_record"]
        assert meeting_record["meeting_id"] == expected["meeting_id"]
        assert_pointer_exists(meeting_record["artifact_pointer"])
        assert split_pointer(meeting_record["artifact_pointer"])[0] == "customer_ops/meetings/escalation_reviews.json"

        demo_link = item["demo_link"]
        assert demo_link["url"] == expected["demo_url"]
        assert_pointer_exists(demo_link["artifact_pointer"])
        assert split_pointer(demo_link["artifact_pointer"])[0] == "customer_ops/demos/demo_catalog.json"

        latest_status = item["latest_status"]
        assert latest_status["state"] == expected["latest_state"]
        assert isinstance(latest_status["summary"], str) and latest_status["summary"].strip()
        assert_pointer_exists(latest_status["artifact_pointer"])
        path_part, fragment = split_pointer(latest_status["artifact_pointer"])
        assert path_part == "customer_ops/slack/escalation_threads.json"
        assert expected["latest_message_id"] in fragment, (
            f"latest_status pointer must identify the latest visible status message for "
            f"{item['commitment_id']}: {latest_status['artifact_pointer']}"
        )


def test_lists_sorted_and_deduplicated():
    data = load_output()
    assert data["affected_customer_ids"] == sorted(set(data["affected_customer_ids"]))

    commitments = data["commitments"]
    commitment_ids = [item["commitment_id"] for item in commitments]
    assert commitment_ids == sorted(set(commitment_ids))

    for item in commitments:
        pr_ids = [pr["pr_id"] for pr in item["fix_prs"]]
        assert pr_ids == sorted(set(pr_ids))
