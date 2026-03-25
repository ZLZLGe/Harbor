import json
import os
from pathlib import Path


ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
REQUEST_PATH = Path(os.environ.get("REQUEST_PATH", str(ROOT_DIR / "release_request.json")))
WAR_ROOM_ROOT = Path(os.environ.get("WAR_ROOM_ROOT", str(ROOT_DIR / "war_room")))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", str(ROOT_DIR / "release_blocker_ledger.json")))

EXPECTED_RELEASE_CANDIDATE = "rc_searchflow_2026_04_rc3"
EXPECTED_BLOCKERS = {
    "BLK-201": {
        "title": "RBAC document filter leaks restricted snippets in export API",
        "owner_employee_id": "eid_23bc77d1",
        "fix_pr_id": "PR-842",
        "missing_signoffs": ["Security"],
    },
    "BLK-204": {
        "title": "Cross-region reindex saturates ingest workers and misses SLA",
        "owner_employee_id": "eid_68b12cd7",
        "fix_pr_id": "PR-847",
        "missing_signoffs": ["QA"],
    },
    "BLK-207": {
        "title": "EU audit log payload omits retention reason code",
        "owner_employee_id": "eid_4fa82c90",
        "fix_pr_id": "PR-851",
        "missing_signoffs": ["Compliance"],
    },
}
EXCLUDED_BLOCKERS = {"BLK-198", "BLK-209", "BLK-210"}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def split_pointer(pointer: str):
    path_part, _, fragment = pointer.partition("#")
    return path_part, fragment


def assert_pointer_exists(pointer: str):
    assert isinstance(pointer, str) and pointer.strip(), f"Invalid pointer: {pointer!r}"
    path_part, fragment = split_pointer(pointer)
    assert path_part.startswith("war_room/"), f"Pointer must use a /root-relative war_room path: {pointer}"
    full_path = ROOT_DIR / path_part
    assert full_path.exists(), f"Pointer path does not exist: {pointer}"
    assert fragment, f"Pointer must include a record fragment: {pointer}"


def load_output():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    return load_json(OUTPUT_PATH)


def latest_status_pointer_options():
    updates = load_json(WAR_ROOM_ROOT / "tracker" / "status_updates.json")
    latest_updates = {}
    for update in updates:
        if update["release_candidate"] != EXPECTED_RELEASE_CANDIDATE:
            continue
        blocker_id = update["blocker_id"]
        current = latest_updates.get(blocker_id)
        if current is None or update["timestamp"] > current["timestamp"]:
            latest_updates[blocker_id] = update

    return {
        blocker_id: {
            f'war_room/tracker/status_updates.json#update_id={update["update_id"]}',
            f'{update["artifact_path"]}#{update["artifact_fragment"]}',
        }
        for blocker_id, update in latest_updates.items()
    }


def test_inputs_exist():
    assert REQUEST_PATH.exists(), f"Missing request file: {REQUEST_PATH}"
    assert WAR_ROOM_ROOT.exists(), f"Missing war room root: {WAR_ROOM_ROOT}"


def test_output_schema_and_expected_values():
    data = load_output()
    assert data["release_candidate"] == EXPECTED_RELEASE_CANDIDATE
    allowed_latest_pointers = latest_status_pointer_options()

    blockers = data["blockers"]
    assert isinstance(blockers, list) and blockers, "blockers must be a non-empty list"
    got_ids = [item["blocker_id"] for item in blockers]
    assert got_ids == sorted(EXPECTED_BLOCKERS.keys())
    assert EXCLUDED_BLOCKERS.isdisjoint(got_ids), f"Excluded blockers leaked into output: {got_ids}"

    for blocker in blockers:
        expected = EXPECTED_BLOCKERS[blocker["blocker_id"]]
        assert blocker["title"] == expected["title"]
        assert blocker["owner_employee_id"] == expected["owner_employee_id"]

        fix_pr = blocker["fix_pr"]
        assert fix_pr["pr_id"] == expected["fix_pr_id"]
        assert_pointer_exists(fix_pr["artifact_pointer"])
        assert split_pointer(fix_pr["artifact_pointer"])[0] == "war_room/prs/release_fix_prs.json"

        latest_status = blocker["latest_status"]
        assert isinstance(latest_status["summary"], str) and latest_status["summary"].strip()
        assert_pointer_exists(latest_status["artifact_pointer"])
        assert latest_status["artifact_pointer"] in allowed_latest_pointers[blocker["blocker_id"]]

        missing = blocker["missing_signoffs"]
        assert isinstance(missing, list) and missing, "missing_signoffs must be a non-empty list"
        missing_teams = [item["team"] for item in missing]
        assert missing_teams == expected["missing_signoffs"]
        for item in missing:
            assert_pointer_exists(item["artifact_pointer"])
            assert split_pointer(item["artifact_pointer"])[0] == "war_room/approvals/signoff_matrix.json"


def test_lists_are_sorted_and_deduplicated():
    data = load_output()
    blockers = data["blockers"]
    ids = [item["blocker_id"] for item in blockers]
    assert ids == sorted(set(ids))

    for blocker in blockers:
        teams = [item["team"] for item in blocker["missing_signoffs"]]
        assert teams == sorted(set(teams))
