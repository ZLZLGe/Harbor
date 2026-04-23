#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import os
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(name):
    with (DATA_DIR / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bool_str(value):
    return "true" if value else "false"


def parse_bool(value):
    return str(value).strip().lower() == "true"


projects = read_csv("capital_projects.csv")
risks = {row["project_id"]: row for row in read_csv("risk_flags.csv")}
cpi = {row["month"]: float(row["cpi"]) for row in read_csv("cpi.csv")}
actions = read_csv("action_catalog.csv")
capacity_rows = read_csv("team_capacity.csv")
rules = read_csv("project_dependencies.csv")

jan_2025_cpi = cpi["2025-01"]
triage_rows = []
selected = []

for project in projects:
    pid = project["project_id"]
    risk = risks[pid]
    baseline_finish = date.fromisoformat(project["baseline_finish"])
    forecast_finish = date.fromisoformat(project["forecast_finish"])
    schedule_variance = (forecast_finish - baseline_finish).days
    normalized_estimate = round(float(project["current_estimate"]) * jan_2025_cpi / cpi[project["estimate_month"]], 2)
    cost_variance = round(normalized_estimate / float(project["approved_budget"]) - 1, 4)
    late = schedule_variance > 30
    over_budget = cost_variance > 0.10
    blocked = parse_bool(risk["unresolved_blocker"])
    high_priority = parse_bool(risk["executive_priority"]) or parse_bool(risk["public_impact"])
    active = project["status"] not in {"Complete", "Cancelled"}
    recover = active and (
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
    elif recover:
        triage_status = "recover"
    else:
        triage_status = "monitor"

    row = {
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
        "normalized_current_estimate": f"{normalized_estimate:.2f}",
        "schedule_variance_days": str(schedule_variance),
        "cost_variance_pct": f"{cost_variance:.4f}",
        "late": bool_str(late),
        "over_budget": bool_str(over_budget),
        "blocked": bool_str(blocked),
        "high_priority": bool_str(high_priority),
        "triage_status": triage_status,
    }
    triage_rows.append(row)
    if recover:
        selected.append((project, row, risk))

triage_columns = [
    "project_id", "agency", "project_name", "borough", "category", "current_phase",
    "baseline_finish", "forecast_finish", "approved_budget", "current_estimate",
    "normalized_current_estimate", "schedule_variance_days", "cost_variance_pct",
    "late", "over_budget", "blocked", "high_priority", "triage_status",
]
with (OUTPUT_DIR / "portfolio_triage.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=triage_columns)
    writer.writeheader()
    writer.writerows(triage_rows)

rule_pairs = {
    (row["current_phase"], row["allowed_action_type"]): row for row in rules
}


def eligible_actions(project, triage, risk):
    phase = project["current_phase"]
    blocked = triage["blocked"] == "true"
    if blocked:
        preferred = {"escalation", "blocker_removal"}
    elif triage["over_budget"] == "true" and float(triage["cost_variance_pct"]) >= 0.15:
        preferred = {"cost_review", f"{phase.lower()}_recovery"}
    else:
        preferred = {f"{phase.lower()}_recovery", "commitment_reset", "cost_review"}

    candidates = []
    for action in actions:
        phases = {p.strip() for p in action["eligible_phases"].split(";")}
        key = (phase, action["action_type"])
        if phase in phases and key in rule_pairs:
            if int(project["percent_complete"]) >= int(rule_pairs[key]["minimum_percent_complete"]):
                candidates.append(action)

    preferred_candidates = [a for a in candidates if a["action_type"] in preferred]
    return sorted(preferred_candidates or candidates, key=lambda a: (int(a["action_priority"]), a["action_id"]))


def priority_key(item):
    project, triage, risk = item
    return (
        0 if triage["blocked"] == "true" else 1,
        0 if (triage["high_priority"] == "true" and parse_bool(risk["public_impact"])) else 1,
        -int(triage["schedule_variance_days"]),
        -float(triage["normalized_current_estimate"]),
        date.fromisoformat(triage["baseline_finish"]),
        project["project_id"],
    )


capacity = {
    (row["week_start"], row["workstream"], row["owner_role"]): float(row["capacity_hours"])
    for row in capacity_rows
}
used = defaultdict(float)
weeks = sorted({row["week_start"] for row in capacity_rows})
plan_rows = []

for project, triage, risk in sorted(selected, key=priority_key):
    candidates = eligible_actions(project, triage, risk)
    if not candidates:
        continue
    placed = False
    for action in candidates:
        for week in weeks:
            cap_key = (week, action["workstream"], action["owner_role"])
            effort = float(action["effort_hours"])
            if used[cap_key] + effort <= capacity.get(cap_key, 0):
                used[cap_key] += effort
                start = date.fromisoformat(week)
                finish = start + timedelta(days=int(action["duration_days"]) - 1)
                rule = rule_pairs[(project["current_phase"], action["action_type"])]
                risk_bits = []
                if triage["blocked"] == "true":
                    risk_bits.append(risk["blocker_type"])
                if triage["late"] == "true":
                    risk_bits.append(f"{triage['schedule_variance_days']} schedule variance days")
                if triage["over_budget"] == "true":
                    risk_bits.append(f"{triage['cost_variance_pct']} cost variance")
                plan_rows.append({
                    "project_id": project["project_id"],
                    "week_start": week,
                    "workstream": action["workstream"],
                    "owner_role": action["owner_role"],
                    "action_id": action["action_id"],
                    "action_name": action["action_name"],
                    "planned_start": start.isoformat(),
                    "planned_finish": finish.isoformat(),
                    "effort_hours": str(int(effort)),
                    "target_status": action["target_status"],
                    "dependency_note": rule["dependency_note"],
                    "risk_note": "; ".join(x for x in risk_bits if x),
                })
                placed = True
                break
        if placed:
            break

plan_columns = [
    "project_id", "week_start", "workstream", "owner_role", "action_id", "action_name",
    "planned_start", "planned_finish", "effort_hours", "target_status",
    "dependency_note", "risk_note",
]
with (OUTPUT_DIR / "recovery_plan.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=plan_columns)
    writer.writeheader()
    writer.writerows(plan_rows)

first_plan_by_project = {}
for row in sorted(plan_rows, key=lambda r: (r["project_id"], r["planned_start"], r["action_id"])):
    first_plan_by_project.setdefault(row["project_id"], row)

updates = []
for pid, row in first_plan_by_project.items():
    risk_note = row["risk_note"] or "remaining schedule and cost exposure"
    updates.append({
        "project_id": pid,
        "target_status": row["target_status"],
        "owner_role": row["owner_role"],
        "week_start": row["week_start"],
        "comment": f"{row['action_name']} planned for week of {row['week_start']}; remaining risk: {risk_note}.",
    })
updates.sort(key=lambda r: r["project_id"])
with (OUTPUT_DIR / "board_updates.json").open("w", encoding="utf-8") as f:
    json.dump({"updates": updates}, f, indent=2)

triage_by_project = {row["project_id"]: row for row in triage_rows}
selected_ids = {row["project_id"] for row in plan_rows}
blocked_count = sum(row["blocked"] == "true" for row in triage_rows)
late_count = sum(row["late"] == "true" for row in triage_rows)
over_budget_count = sum(row["over_budget"] == "true" for row in triage_rows)

top_risk = sorted(
    [triage_by_project[pid] for pid in selected_ids],
    key=lambda r: (r["blocked"] != "true", -int(r["schedule_variance_days"]), -float(r["normalized_current_estimate"]), r["project_id"]),
)[:5]

bottlenecks = []
for key, cap in capacity.items():
    utilization = used[key] / cap if cap else 0
    bottlenecks.append((utilization, used[key], cap, key))
bottleneck = max(bottlenecks, key=lambda x: (x[0], x[1], x[3]))

summary = [
    "# Executive Summary",
    "",
    f"Total projects reviewed: {len(projects)}.",
    f"Projects selected for recovery: {len(selected_ids)}.",
    f"Blocked projects: {blocked_count}.",
    f"Late projects: {late_count}.",
    f"Over-budget projects: {over_budget_count}.",
    "",
    "Top five highest-risk recovery projects:",
]
for row in top_risk:
    summary.append(
        f"- {row['project_id']} - {row['project_name']}: blocked={row['blocked']}, "
        f"schedule_variance_days={row['schedule_variance_days']}, cost_variance_pct={row['cost_variance_pct']}."
    )
summary.extend([
    "",
    f"Main capacity bottleneck by workstream: {bottleneck[3][1]} / {bottleneck[3][2]} "
    f"in week {bottleneck[3][0]} at {bottleneck[1]:.0f}/{bottleneck[2]:.0f} hours.",
    "",
    "Prioritization approach: blocked projects were planned first, then public-impact high-priority projects, "
    "then larger schedule variance, larger normalized cost exposure, earlier baseline finish date, and project ID.",
    "",
    "## Project: Municipal Capital Recovery Plan",
    "",
    "**Goal**: Stabilize delayed, blocked, and over-budget capital projects with a feasible 6-week recovery plan.",
    "**Timeline**: 6 weeks starting 2025-07-07.",
    "**Team**: Program Manager, Procurement Lead, Design Lead, Construction Manager, Inspector, and Cost Analyst.",
    "**Constraints**: Use only allowed actions, respect phase gates, preserve weekly capacity, and escalate blockers first.",
    "",
    "## Milestones",
    "",
    "| Milestone | Target Week | Owner | Success Criteria |",
    "|---|---|---|---|",
    "| Recovery scope confirmed | 2025-07-07 | Program Manager | All selected projects have a valid first action |",
    "| Blockers escalated | 2025-07-14 | Program Manager | Blocked projects have escalation or blocker-removal actions started |",
    "| Recovery actions underway | 2025-07-28 | Workstream Leads | Phase-eligible recovery actions are scheduled within capacity |",
    "",
    "## Phase 1: Triage and Escalation (Weeks 1-2)",
    "",
    "| Phase | Focus |",
    "|---|---|",
    "| Weeks 1-2 | Triage, blocker escalation, and first recovery actions |",
    "| Weeks 3-4 | Cost reviews, procurement/design/construction recovery, and commitment resets |",
    "| Weeks 5-6 | Governance follow-up and remaining stakeholder alignment |",
    "",
    "## Dependencies Map",
    "",
    "```text",
    "Triage -> Blocker escalation/removal -> Phase recovery action -> Cost review -> Commitment reset",
    "```",
    "",
    "## Risks & Mitigation",
    "",
    "| Risk | Mitigation |",
    "|---|---|",
    "| Unresolved blocker | Escalate or remove blocker before downstream recovery work |",
    "| Cost exposure | Schedule cost exposure review within controls capacity |",
    "| Public-impact delay | Prioritize public-impact high-priority projects after blocked work |",
    "",
    "## Resource Allocation",
    "",
    "| Workstream | Planned Hours | Capacity Hours |",
    "|---|---:|---:|",
])
for workstream in sorted({key[1] for key in capacity}):
    planned = sum(used[key] for key in used if key[1] == workstream)
    available = sum(cap for key, cap in capacity.items() if key[1] == workstream)
    summary.append(f"| {workstream} | {planned:.0f} | {available:.0f} |")
with (OUTPUT_DIR / "executive_summary.md").open("w", encoding="utf-8") as f:
    f.write("\n".join(summary) + "\n")
PY
