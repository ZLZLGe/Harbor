#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
REQUEST_PATH="${REQUEST_PATH:-$ROOT_DIR/escalation_request.json}"
OPS_ROOT="${OPS_ROOT:-$ROOT_DIR/customer_ops}"
OUTPUT_PATH="${OUTPUT_PATH:-$ROOT_DIR/customer_escalation_brief.json}"

python3 - "$REQUEST_PATH" "$OPS_ROOT" "$OUTPUT_PATH" <<'PY'
import json
import sys
from datetime import datetime
from pathlib import Path


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_ts(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


request_path = Path(sys.argv[1])
ops_root = Path(sys.argv[2])
output_path = Path(sys.argv[3])

request = load_json(request_path)
briefs = load_json(ops_root / "crm" / "escalation_briefs.json")
commitments = load_json(ops_root / "commitments" / "commitment_register.json")
meetings = load_json(ops_root / "meetings" / "escalation_reviews.json")
prs = load_json(ops_root / "prs" / "fix_prs.json")
demos = load_json(ops_root / "demos" / "demo_catalog.json")
messages = load_json(ops_root / "slack" / "escalation_threads.json")

account_id = request["account_id"]
escalation_id = request["escalation_id"]
cutoff = parse_ts(request["cutoff"])

brief = next(
    item
    for item in briefs
    if item["account_id"] == account_id and item["escalation_id"] == escalation_id
)

visible_commitments = set(brief.get("customer_visible_commitments", []))

selected = []
for item in commitments:
    if item["account_id"] != account_id or item["escalation_id"] != escalation_id:
        continue
    if item["commitment_id"] not in visible_commitments:
        continue
    if not item["customer_committed"] or item["status"] != "active":
        continue

    meeting = next(
        record
        for record in meetings
        if record["meeting_id"] == item["source_meeting_id"]
        and record["account_id"] == account_id
        and record["escalation_id"] == escalation_id
        and any(
            decision["commitment_id"] == item["commitment_id"]
            and decision["decision"] == "commit_to_customer"
            for decision in record["decisions"]
        )
    )

    matched_prs = sorted(
        [
            {
                "pr_id": pr["pr_id"],
                "artifact_pointer": f"customer_ops/prs/fix_prs.json#pr_id={pr['pr_id']}",
            }
            for pr in prs
            if pr["account_id"] == account_id
            and pr["escalation_id"] == escalation_id
            and pr["commitment_id"] == item["commitment_id"]
            and pr["status"] == "merged"
            and pr["change_type"] == "direct_fix"
            and parse_ts(pr["merged_at"]) <= cutoff
        ],
        key=lambda pr: pr["pr_id"],
    )

    demo_candidates = [
        demo
        for demo in demos
        if demo["account_id"] == account_id
        and demo["escalation_id"] == escalation_id
        and demo["commitment_id"] == item["commitment_id"]
        and demo["status"] == "shared"
        and demo["audience"] == "customer"
        and parse_ts(demo["shared_at"]) <= cutoff
    ]
    demo = max(demo_candidates, key=lambda record: parse_ts(record["shared_at"]))

    status_candidates = [
        message
        for message in messages
        if message["account_id"] == account_id
        and message["escalation_id"] == escalation_id
        and message["commitment_id"] == item["commitment_id"]
        and message["visibility"] == "customer"
        and message["kind"] in {"customer_commitment", "status_update"}
        and parse_ts(message["timestamp"]) <= cutoff
    ]
    latest_status = max(status_candidates, key=lambda record: parse_ts(record["timestamp"]))

    selected.append(
        {
            "commitment_id": item["commitment_id"],
            "summary": item["summary"],
            "owner_employee_id": item["owner_employee_id"],
            "fix_prs": matched_prs,
            "meeting_record": {
                "meeting_id": meeting["meeting_id"],
                "artifact_pointer": f"customer_ops/meetings/escalation_reviews.json#meeting_id={meeting['meeting_id']}",
            },
            "demo_link": {
                "url": demo["url"],
                "artifact_pointer": f"customer_ops/demos/demo_catalog.json#demo_id={demo['demo_id']}",
            },
            "latest_status": {
                "state": latest_status["status_state"],
                "summary": latest_status["text"],
                "artifact_pointer": f"customer_ops/slack/escalation_threads.json#message_id={latest_status['message_id']}",
            },
        }
    )

result = {
    "account_id": account_id,
    "escalation_id": escalation_id,
    "affected_customer_ids": sorted(set(brief["affected_customer_ids"])),
    "commitments": sorted(selected, key=lambda item: item["commitment_id"]),
}

output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
