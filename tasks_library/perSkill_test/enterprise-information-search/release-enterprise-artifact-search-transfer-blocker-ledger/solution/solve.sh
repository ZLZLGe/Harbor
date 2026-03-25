#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("TASK_ROOT", "/root"))
REQUEST_PATH = Path(os.environ.get("REQUEST_PATH", str(ROOT / "release_request.json")))
WAR_ROOM = Path(os.environ.get("WAR_ROOM_ROOT", str(ROOT / "war_room")))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", str(ROOT / "release_blocker_ledger.json")))


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


request = load_json(REQUEST_PATH)
target_rc = request["release_candidate"]

blockers = load_json(WAR_ROOM / "tracker" / "blocker_tracker.json")
updates = load_json(WAR_ROOM / "tracker" / "status_updates.json")
prs = load_json(WAR_ROOM / "prs" / "release_fix_prs.json")
signoffs = load_json(WAR_ROOM / "approvals" / "signoff_matrix.json")

active_statuses = {"open", "monitoring", "awaiting_signoff"}

updates_by_id = {item["update_id"]: item for item in updates}
prs_by_blocker = {}
for pr in prs:
    if pr.get("release_candidate") != target_rc:
        continue
    for blocker_id in pr.get("linked_blockers", []):
        prs_by_blocker.setdefault(blocker_id, []).append(pr)

signoffs_by_blocker = {}
for row in signoffs:
    if row.get("release_candidate") != target_rc:
        continue
    signoffs_by_blocker.setdefault(row["blocker_id"], []).append(row)

result = []
for blocker in blockers:
    if blocker.get("release_candidate") != target_rc:
        continue
    if blocker.get("status") not in active_statuses:
        continue

    update = updates_by_id[blocker["latest_update_ref"]]
    blocker_prs = prs_by_blocker.get(blocker["blocker_id"], [])
    if not blocker_prs:
        continue
    blocker_prs.sort(key=lambda item: item["pr_id"])
    chosen_pr = blocker_prs[0]

    pending_signoffs = []
    for row in signoffs_by_blocker.get(blocker["blocker_id"], []):
        if row.get("status") == "pending":
            pending_signoffs.append(
                {
                    "team": row["team"],
                    "artifact_pointer": f'{row["artifact_path"]}#{row["artifact_fragment"]}',
                }
            )
    pending_signoffs.sort(key=lambda item: item["team"])

    result.append(
        {
            "blocker_id": blocker["blocker_id"],
            "title": blocker["title"],
            "owner_employee_id": blocker["owner_employee_id"],
            "fix_pr": {
                "pr_id": chosen_pr["pr_id"],
                "artifact_pointer": f'war_room/prs/release_fix_prs.json#pr_id={chosen_pr["pr_id"]}',
            },
            "latest_status": {
                "summary": update["summary"],
                "artifact_pointer": f'{update["artifact_path"]}#{update["artifact_fragment"]}',
            },
            "missing_signoffs": pending_signoffs,
        }
    )

result.sort(key=lambda item: item["blocker_id"])

with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(
        {
            "release_candidate": target_rc,
            "blockers": result,
        },
        f,
        ensure_ascii=False,
        indent=2,
    )
    f.write("\n")
PY
