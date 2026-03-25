#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
from datetime import date
from pathlib import Path

ROOT = Path("/root")
REQUEST_PATH = ROOT / "audit_request.json"
CONTROL_PATH = ROOT / "audit_prep" / "controls" / "control_register.json"
POLICY_PATH = ROOT / "audit_prep" / "policies" / "policy_documents.json"
APPROVAL_PATH = ROOT / "audit_prep" / "approvals" / "approval_threads.json"
PR_PATH = ROOT / "audit_prep" / "prs" / "remediation_prs.json"
EXCEPTION_PATH = ROOT / "audit_prep" / "exceptions" / "exception_register.json"
OUTPUT_PATH = ROOT / "control_audit_trace.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_date(value):
    if not value:
        return date.min
    return date.fromisoformat(value)


def parse_version(value: str):
    parts = []
    for part in value.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(part)
    return tuple(parts)


request = load_json(REQUEST_PATH)
controls = load_json(CONTROL_PATH)
policies = load_json(POLICY_PATH)
approvals = load_json(APPROVAL_PATH)
prs = load_json(PR_PATH)
exceptions = load_json(EXCEPTION_PATH)

control = next(item for item in controls if item["control_id"] == request["control_id"])
cutoff = parse_date(request["audit_cutoff"])
gap_ticket_ids = set(control["gap_ticket_ids"])

eligible_policies = [
    item
    for item in policies
    if control["control_id"] in item.get("control_ids", [])
    and item.get("policy_family") == control["policy_family"]
    and item.get("status") == "final"
    and parse_date(item.get("effective_date")) <= cutoff
]

selected_policy = sorted(
    eligible_policies,
    key=lambda item: (parse_date(item["effective_date"]), parse_version(item["version"])),
)[-1]

approver_rows = []
seen_approvers = set()
for row in approvals:
    if (
        row.get("doc_id") == selected_policy["doc_id"]
        and row.get("thread_id") == selected_policy["approval_thread_id"]
        and row.get("action") == "APPROVED"
    ):
        employee_id = row["employee_id"]
        if employee_id not in seen_approvers:
            seen_approvers.add(employee_id)
            approver_rows.append(
                {
                    "employee_id": employee_id,
                    "artifact_pointer": f"audit_prep/approvals/approval_threads.json#message_id={row['message_id']}",
                }
            )

approver_rows.sort(key=lambda item: item["employee_id"])

remediation_rows = []
seen_prs = set()
for row in prs:
    if (
        control["control_id"] in row.get("control_ids", [])
        and row.get("audit_cycle") == request["audit_cycle"]
        and row.get("status") == "merged"
        and row.get("remediation_scope") == "direct_fix"
        and row.get("policy_doc_id") == selected_policy["doc_id"]
        and gap_ticket_ids.intersection(row.get("gap_ticket_ids", []))
    ):
        pr_id = row["pr_id"]
        if pr_id not in seen_prs:
            seen_prs.add(pr_id)
            remediation_rows.append(
                {
                    "pr_id": pr_id,
                    "artifact_pointer": f"audit_prep/prs/remediation_prs.json#pr_id={pr_id}",
                }
            )

remediation_rows.sort(key=lambda item: item["pr_id"])

eligible_exceptions = [
    item
    for item in exceptions
    if item.get("control_id") == control["control_id"]
    and item.get("audit_cycle") == request["audit_cycle"]
    and item.get("status") == "approved"
    and item.get("active") is True
    and parse_date(item.get("approval_date")) <= cutoff
]

selected_exception = sorted(
    eligible_exceptions,
    key=lambda item: parse_date(item["approval_date"]),
)[-1]

result = {
    "control_id": control["control_id"],
    "policy_document": {
        "doc_id": selected_policy["doc_id"],
        "artifact_pointer": f"audit_prep/policies/policy_documents.json#doc_id={selected_policy['doc_id']}",
    },
    "remediation_prs": remediation_rows,
    "approver_employee_ids": approver_rows,
    "exception": {
        "url": selected_exception["url"],
        "artifact_pointer": f"audit_prep/exceptions/exception_register.json#exception_id={selected_exception['exception_id']}",
    },
}

with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
PY
