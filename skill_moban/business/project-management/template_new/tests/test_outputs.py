import csv
import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))

EXPECTED_INPUT_HASHES = {
    "action_catalog.csv": "d7162eb9c74053cd07c294d4511e60c68d3c0bdb9b3a923fc90953122ed51327",
    "capital_projects.csv": "8bf58d88d274831e725eccbdc7fc3a93fa94f3c0d7ae5ed37e6f829b4efa90be",
    "cpi.csv": "ab3f503738fa6ffc4487139812a28ba70091106da6038680b68a795fb749a38d",
    "project_dependencies.csv": "81e836a30ae0b16bde2f0c9416b40c1e8dd88b01db5b3032a9ee6a89da630754",
    "risk_flags.csv": "099217d6a27e8c13fbda1b1026116a9dd581ff70db72c6ab7e1a3efcc4df215d",
    "team_capacity.csv": "15bbbf8337cf57ba2c5a3012eafdb13e66a3d642fefbc3dd8aafcecd7406b31e",
}

TRIAGE_COLUMNS = [
    "project_id", "agency", "project_name", "borough", "category", "current_phase",
    "baseline_finish", "forecast_finish", "approved_budget", "current_estimate",
    "normalized_current_estimate", "schedule_variance_days", "cost_variance_pct",
    "late", "over_budget", "blocked", "high_priority", "triage_status",
]

PLAN_COLUMNS = [
    "project_id", "week_start", "workstream", "owner_role", "action_id", "action_name",
    "planned_start", "planned_finish", "effort_hours", "target_status",
    "dependency_note", "risk_note",
]

ALLOWED_TRIAGE_STATUS = {"monitor", "recover", "escalate", "complete", "exclude"}
ALLOWED_TARGET_STATUS = {"Blocked", "Escalated", "Recovery Planned", "In Progress", "Ready for Review", "On Track"}
EXPECTED_OUTPUT_FILES = {
    "portfolio_triage.csv",
    "recovery_plan.csv",
    "board_updates.json",
    "executive_summary.md",
}


def _read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _parse_bool(value):
    return str(value).strip().lower() == "true"


def _load_inputs():
    projects = _read_csv(DATA_DIR / "capital_projects.csv")
    risks = {row["project_id"]: row for row in _read_csv(DATA_DIR / "risk_flags.csv")}
    cpi = {row["month"]: float(row["cpi"]) for row in _read_csv(DATA_DIR / "cpi.csv")}
    actions = {row["action_id"]: row for row in _read_csv(DATA_DIR / "action_catalog.csv")}
    rules = _read_csv(DATA_DIR / "project_dependencies.csv")
    capacity = _read_csv(DATA_DIR / "team_capacity.csv")
    return projects, risks, cpi, actions, rules, capacity


def _expected_triage():
    projects, risks, cpi, _, _, _ = _load_inputs()
    jan_cpi = cpi["2025-01"]
    expected = {}
    for project in projects:
        pid = project["project_id"]
        risk = risks[pid]
        schedule_variance = (
            date.fromisoformat(project["forecast_finish"]) - date.fromisoformat(project["baseline_finish"])
        ).days
        normalized = round(float(project["current_estimate"]) * jan_cpi / cpi[project["estimate_month"]], 2)
        cost_variance = round(normalized / float(project["approved_budget"]) - 1, 4)
        late = schedule_variance > 30
        over_budget = cost_variance > 0.10
        blocked = _parse_bool(risk["unresolved_blocker"])
        high_priority = _parse_bool(risk["executive_priority"]) or _parse_bool(risk["public_impact"])
        active = project["status"] not in {"Complete", "Cancelled"}
        selected = active and (
            blocked
            or (high_priority and (late or over_budget))
            or (schedule_variance > 60 and cost_variance > 0.15)
        )
        if project["status"] == "Complete":
            triage_status = "complete"
        elif project["status"] == "Cancelled":
            triage_status = "exclude"
        elif blocked:
            triage_status = "escalate"
        elif selected:
            triage_status = "recover"
        else:
            triage_status = "monitor"
        expected[pid] = {
            "project_id": pid,
            "agency": project["agency"],
            "project_name": project["project_name"],
            "borough": project["borough"],
            "category": project["category"],
            "current_phase": project["current_phase"],
            "baseline_finish": project["baseline_finish"],
            "forecast_finish": project["forecast_finish"],
            "approved_budget": project["approved_budget"],
            "current_estimate": project["current_estimate"],
            "normalized_current_estimate": normalized,
            "schedule_variance_days": schedule_variance,
            "cost_variance_pct": cost_variance,
            "late": late,
            "over_budget": over_budget,
            "blocked": blocked,
            "high_priority": high_priority,
            "triage_status": triage_status,
            "selected": selected,
            "status": project["status"],
            "percent_complete": int(project["percent_complete"]),
        }
    return expected


def _read_triage_output():
    return _read_csv(OUTPUT_DIR / "portfolio_triage.csv")


def _read_plan_output():
    return _read_csv(OUTPUT_DIR / "recovery_plan.csv")


def test_guardrail_input_files_are_unchanged():
    for filename, expected_hash in EXPECTED_INPUT_HASHES.items():
        path = DATA_DIR / filename
        assert path.exists(), f"Missing input file: {filename}"
        assert _hash_file(path) == expected_hash, f"Input file was modified: {filename}"


def test_guardrail_only_expected_output_files_are_created():
    assert OUTPUT_DIR.exists(), "Output directory does not exist"
    files = {p.name for p in OUTPUT_DIR.iterdir() if p.is_file()}
    assert files == EXPECTED_OUTPUT_FILES, f"Unexpected output files: {sorted(files - EXPECTED_OUTPUT_FILES)}"


def test_main_required_output_files_exist():
    for filename in EXPECTED_OUTPUT_FILES:
        assert (OUTPUT_DIR / filename).exists(), f"Missing required output file: {filename}"


def test_main_portfolio_triage_schema_and_math():
    rows = _read_triage_output()
    expected = _expected_triage()
    assert rows, "portfolio_triage.csv is empty"
    assert list(rows[0].keys()) == TRIAGE_COLUMNS, "portfolio_triage.csv columns do not match the requested schema"
    assert {row["project_id"] for row in rows} == set(expected), "Triage output must include every input project exactly once"

    seen = set()
    for row in rows:
        pid = row["project_id"]
        assert pid not in seen, f"Duplicate triage row for {pid}"
        seen.add(pid)
        exp = expected[pid]
        for col in ["agency", "project_name", "borough", "category", "current_phase", "baseline_finish", "forecast_finish"]:
            assert row[col] == exp[col], f"{pid} has incorrect {col}"
        date.fromisoformat(row["baseline_finish"])
        date.fromisoformat(row["forecast_finish"])
        assert abs(float(row["normalized_current_estimate"]) - exp["normalized_current_estimate"]) <= 0.01
        assert re.fullmatch(r"-?\d+\.\d{2}", row["normalized_current_estimate"]), "normalized_current_estimate must keep 2 decimals"
        assert int(row["schedule_variance_days"]) == exp["schedule_variance_days"]
        assert abs(float(row["cost_variance_pct"]) - exp["cost_variance_pct"]) <= 0.0001
        assert re.fullmatch(r"-?\d+\.\d{4}", row["cost_variance_pct"]), "cost_variance_pct must keep 4 decimals"
        for bool_col in ["late", "over_budget", "blocked", "high_priority"]:
            assert row[bool_col] in {"true", "false"}, f"{bool_col} must be true or false"
            assert _parse_bool(row[bool_col]) == exp[bool_col], f"{pid} has incorrect {bool_col}"
        assert row["triage_status"] in ALLOWED_TRIAGE_STATUS
        assert row["triage_status"] == exp["triage_status"], f"{pid} has incorrect triage_status"


def test_main_recovery_plan_project_selection_and_schema():
    expected = _expected_triage()
    expected_selected = {pid for pid, row in expected.items() if row["selected"]}
    plan_rows = _read_plan_output()
    assert plan_rows, "recovery_plan.csv is empty"
    assert list(plan_rows[0].keys()) == PLAN_COLUMNS, "recovery_plan.csv columns do not match the requested schema"
    planned_projects = {row["project_id"] for row in plan_rows}
    assert planned_projects == expected_selected, "Recovery plan must include exactly the selected recovery projects"


def test_main_recovery_plan_actions_dates_rules_and_capacity():
    expected = _expected_triage()
    _, _, _, actions, rules, capacity_rows = _load_inputs()
    rule_map = {(row["current_phase"], row["allowed_action_type"]): row for row in rules}
    capacity = {
        (row["week_start"], row["workstream"], row["owner_role"]): float(row["capacity_hours"])
        for row in capacity_rows
    }
    weeks = sorted({row["week_start"] for row in capacity_rows})
    window_start = date.fromisoformat(weeks[0])
    window_end = window_start + timedelta(weeks=6) - timedelta(days=1)
    used = defaultdict(float)
    rows_by_project = defaultdict(list)

    for row in _read_plan_output():
        pid = row["project_id"]
        rows_by_project[pid].append(row)
        assert row["action_id"] in actions, f"{pid} uses an action not listed in action_catalog.csv"
        action = actions[row["action_id"]]
        assert row["action_name"] == action["action_name"], f"{pid} action_name does not match action_catalog.csv"
        assert row["workstream"] == action["workstream"], f"{pid} workstream does not match action_catalog.csv"
        assert row["owner_role"] == action["owner_role"], f"{pid} owner_role does not match action_catalog.csv"
        assert row["target_status"] == action["target_status"], f"{pid} target_status does not match action_catalog.csv"
        assert row["target_status"] in ALLOWED_TARGET_STATUS
        assert expected[pid]["current_phase"] in {p.strip() for p in action["eligible_phases"].split(";")}
        rule = rule_map.get((expected[pid]["current_phase"], action["action_type"]))
        assert rule, f"{pid} violates project_dependencies.csv action-type rules"
        assert expected[pid]["percent_complete"] >= int(rule["minimum_percent_complete"])
        assert row["dependency_note"].strip(), f"{pid} dependency_note must not be empty"
        start = date.fromisoformat(row["planned_start"])
        finish = date.fromisoformat(row["planned_finish"])
        week_start = date.fromisoformat(row["week_start"])
        assert window_start <= start <= finish <= window_end, f"{pid} planned dates must be inside the 6-week window"
        assert start >= week_start and start < week_start + timedelta(days=7), f"{pid} planned_start must fall in week_start"
        assert int(float(row["effort_hours"])) == int(float(action["effort_hours"])), f"{pid} effort_hours must match action_catalog.csv"
        cap_key = (row["week_start"], row["workstream"], row["owner_role"])
        assert cap_key in capacity, f"{pid} uses a workstream/role/week with no capacity"
        used[cap_key] += float(row["effort_hours"])

    for cap_key, used_hours in used.items():
        assert used_hours <= capacity[cap_key] + 1e-9, f"Capacity exceeded for {cap_key}: {used_hours} > {capacity[cap_key]}"

    for pid, plan_rows in rows_by_project.items():
        plan_rows.sort(key=lambda r: (r["planned_start"], r["action_id"]))
        first_action = actions[plan_rows[0]["action_id"]]
        if expected[pid]["blocked"]:
            first_rule = rule_map[(expected[pid]["current_phase"], first_action["action_type"])]
            assert _parse_bool(first_rule["must_be_first_if_blocked"]), f"{pid} is blocked, so its first action must remove or escalate the blocker"


def test_main_board_updates_match_recovery_plan():
    plan_rows = _read_plan_output()
    planned_projects = {row["project_id"] for row in plan_rows}
    plan_tuples = {
        (row["project_id"], row["target_status"], row["owner_role"], row["week_start"])
        for row in plan_rows
    }
    with (OUTPUT_DIR / "board_updates.json").open(encoding="utf-8") as f:
        payload = json.load(f)
    assert isinstance(payload, dict), "board_updates.json must contain a JSON object"
    assert isinstance(payload.get("updates"), list), "board_updates.json must contain an updates array"
    updates = payload["updates"]
    assert {row.get("project_id") for row in updates} == planned_projects, "Each recovery project must have exactly one board update"
    assert len(updates) == len(planned_projects), "Board updates must not contain duplicate project updates"
    for update in updates:
        required = {"project_id", "target_status", "owner_role", "week_start", "comment"}
        assert set(update) == required, f"Board update has incorrect fields: {update}"
        tup = (update["project_id"], update["target_status"], update["owner_role"], update["week_start"])
        assert tup in plan_tuples, f"Board update does not match any recovery plan row: {update}"
        assert len(str(update["comment"]).strip()) >= 40, "Board update comment must explain action and remaining risk"


def test_main_executive_summary_contains_required_metrics():
    expected = _expected_triage()
    selected = [row for row in expected.values() if row["selected"]]
    blocked_count = sum(row["blocked"] for row in expected.values())
    late_count = sum(row["late"] for row in expected.values())
    over_budget_count = sum(row["over_budget"] for row in expected.values())
    text = (OUTPUT_DIR / "executive_summary.md").read_text(encoding="utf-8")
    assert str(len(expected)) in text, "Executive summary must include total projects reviewed"
    assert str(len(selected)) in text, "Executive summary must include number of recovery projects"
    assert str(blocked_count) in text, "Executive summary must include blocked project count"
    assert str(late_count) in text, "Executive summary must include late project count"
    assert str(over_budget_count) in text, "Executive summary must include over-budget project count"
    assert "bottleneck" in text.lower() or "瓶颈" in text, "Executive summary must identify the main capacity bottleneck"
    assert "prioritization" in text.lower() or "优先" in text, "Executive summary must explain prioritization"
    required_project_plan_markers = [
        "## Project:",
        "**Goal**:",
        "**Timeline**:",
        "**Team**:",
        "**Constraints**:",
        "## Milestones",
        "## Phase 1:",
        "## Dependencies Map",
        "## Risks & Mitigation",
        "## Resource Allocation",
    ]
    for marker in required_project_plan_markers:
        assert marker in text, f"Executive summary must follow the project-planner appendix format and include: {marker}"
    selected_ids_in_text = [row["project_id"] for row in selected if row["project_id"] in text]
    assert len(selected_ids_in_text) >= 5, "Executive summary must list at least five recovery projects as top risks"
    for row in selected:
        if row["blocked"]:
            assert row["project_id"] in text, f"Blocked high-risk project {row['project_id']} is missing from summary"
