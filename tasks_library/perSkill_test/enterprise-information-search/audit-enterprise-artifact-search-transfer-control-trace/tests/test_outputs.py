import json
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
REQUEST_PATH = Path(os.environ.get("REQUEST_PATH", str(ROOT_DIR / "audit_request.json")))
AUDIT_ROOT = Path(os.environ.get("AUDIT_ROOT", str(ROOT_DIR / "audit_prep")))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", str(ROOT_DIR / "control_audit_trace.json")))

EXPECTED_CONTROL_ID = "CTRL-104"
EXPECTED_POLICY_DOC_ID = "POL-ACCESS-RECERT-v3.1"
EXPECTED_PR_IDS = ["PR-2142", "PR-2170"]
EXPECTED_APPROVER_IDS = ["eid_11c2f39a", "eid_7d4e12bc"]
EXPECTED_EXCEPTION_URL = "https://audit.example.internal/exceptions/EX-104-B"
EXCLUDED_PR_IDS = {"PR-2130", "PR-2181", "PR-2194", "PR-2201"}
EXCLUDED_APPROVER_IDS = {"eid_00c91aa1", "eid_99a0ba17", "eid_2bbf9011"}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def split_pointer(pointer: str):
    path_part, _, fragment = pointer.partition("#")
    return path_part, fragment


def assert_pointer_exists(pointer: str):
    assert isinstance(pointer, str) and pointer.strip(), f"Invalid pointer: {pointer!r}"
    path_part, fragment = split_pointer(pointer)
    assert path_part.startswith("audit_prep/"), f"Pointer must use a /root-relative audit_prep path: {pointer}"
    full_path = ROOT_DIR / path_part
    assert full_path.exists(), f"Pointer path does not exist: {pointer}"
    assert fragment, f"Pointer must include a record fragment: {pointer}"


def load_output():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    return load_json(OUTPUT_PATH)


def test_inputs_exist():
    assert REQUEST_PATH.exists(), f"Missing request file: {REQUEST_PATH}"
    assert AUDIT_ROOT.exists(), f"Missing audit root: {AUDIT_ROOT}"


def test_output_schema_and_expected_values():
    data = load_output()
    assert data["control_id"] == EXPECTED_CONTROL_ID

    policy_document = data["policy_document"]
    assert policy_document["doc_id"] == EXPECTED_POLICY_DOC_ID
    assert_pointer_exists(policy_document["artifact_pointer"])
    assert split_pointer(policy_document["artifact_pointer"])[0] == "audit_prep/policies/policy_documents.json"

    remediation_prs = data["remediation_prs"]
    assert isinstance(remediation_prs, list) and remediation_prs, "remediation_prs must be a non-empty list"
    pr_ids = [item["pr_id"] for item in remediation_prs]
    assert pr_ids == EXPECTED_PR_IDS
    assert EXCLUDED_PR_IDS.isdisjoint(pr_ids)
    for item in remediation_prs:
        assert_pointer_exists(item["artifact_pointer"])
        assert split_pointer(item["artifact_pointer"])[0] == "audit_prep/prs/remediation_prs.json"

    approvers = data["approver_employee_ids"]
    assert isinstance(approvers, list) and approvers, "approver_employee_ids must be a non-empty list"
    approver_ids = [item["employee_id"] for item in approvers]
    assert approver_ids == EXPECTED_APPROVER_IDS
    assert EXCLUDED_APPROVER_IDS.isdisjoint(approver_ids)
    for item in approvers:
        assert_pointer_exists(item["artifact_pointer"])
        assert split_pointer(item["artifact_pointer"])[0] == "audit_prep/approvals/approval_threads.json"

    exception = data["exception"]
    assert exception["url"] == EXPECTED_EXCEPTION_URL
    assert_pointer_exists(exception["artifact_pointer"])
    assert split_pointer(exception["artifact_pointer"])[0] == "audit_prep/exceptions/exception_register.json"


def test_lists_are_sorted_and_deduplicated():
    data = load_output()

    pr_ids = [item["pr_id"] for item in data["remediation_prs"]]
    approver_ids = [item["employee_id"] for item in data["approver_employee_ids"]]

    assert pr_ids == sorted(set(pr_ids))
    assert approver_ids == sorted(set(approver_ids))
