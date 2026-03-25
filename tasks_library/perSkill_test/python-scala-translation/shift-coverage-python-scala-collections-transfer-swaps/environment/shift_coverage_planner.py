from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ShiftNeed:
    date: str
    slot: str
    role: str
    required_staff: int


@dataclass(frozen=True)
class EmployeeSkill:
    employee_id: str
    roles: tuple[str, ...]
    preferred_slots: tuple[str, ...]
    unavailable_dates: tuple[str, ...]


@dataclass(frozen=True)
class LeavePreference:
    employee_id: str
    date: str
    avoid_slots: tuple[str, ...]
    priority: int
    note: str


@dataclass(frozen=True)
class CoverageGap:
    date: str
    slot: str
    role: str
    required_staff: int
    assigned_employees: tuple[str, ...]
    missing_count: int


@dataclass(frozen=True)
class EmployeeConflict:
    employee_id: str
    date: str
    slot: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class SwapSuggestion:
    date: str
    slot: str
    role: str
    from_employee: str
    to_employee: str
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PlanningResult:
    gaps: tuple[CoverageGap, ...]
    conflicts: tuple[EmployeeConflict, ...]
    suggestions: tuple[SwapSuggestion, ...]


def _split_pipe(value: str, *, lower: bool = False) -> tuple[str, ...]:
    parts = []
    for raw_part in value.split("|"):
        part = raw_part.strip()
        if not part:
            continue
        parts.append(part.lower() if lower else part)
    return tuple(parts)


def _read_rows(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            cleaned = {(key or "").strip(): (value or "").strip() for key, value in row.items()}
            rows.append(cleaned)
        return rows


def load_shift_needs(path: str) -> list[ShiftNeed]:
    rows = _read_rows(path)
    needs = [
        ShiftNeed(
            date=row["date"],
            slot=row["slot"].lower(),
            role=row["role"].lower(),
            required_staff=int(row["required_staff"]),
        )
        for row in rows
    ]
    return sorted(needs, key=lambda need: (need.date, need.slot, need.role))


def load_employee_skills(path: str) -> list[EmployeeSkill]:
    rows = _read_rows(path)
    skills = [
        EmployeeSkill(
            employee_id=row["employee_id"],
            roles=_split_pipe(row["roles"], lower=True),
            preferred_slots=_split_pipe(row["preferred_slots"], lower=True),
            unavailable_dates=_split_pipe(row["unavailable_dates"]),
        )
        for row in rows
    ]
    return sorted(skills, key=lambda skill: skill.employee_id)


def load_leave_preferences(path: str) -> list[LeavePreference]:
    rows = _read_rows(path)
    preferences = [
        LeavePreference(
            employee_id=row["employee_id"],
            date=row["date"],
            avoid_slots=_split_pipe(row["avoid_slots"], lower=True),
            priority=int(row["priority"]),
            note=row["note"],
        )
        for row in rows
    ]
    return sorted(preferences, key=lambda pref: (pref.date, pref.employee_id, pref.priority, pref.note))


def _leave_priority(
    preferences: Iterable[LeavePreference],
    employee_id: str,
    date: str,
    slot: str,
) -> int:
    matching = [
        pref.priority
        for pref in preferences
        if pref.employee_id == employee_id
        and pref.date == date
        and ("all" in pref.avoid_slots or slot in pref.avoid_slots)
    ]
    return max(matching, default=0)


def _prefers_slot(skill: EmployeeSkill, slot: str) -> bool:
    return slot in skill.preferred_slots


def _can_cover(skill: EmployeeSkill, role: str, date: str) -> bool:
    return role in skill.roles and date not in skill.unavailable_dates


def plan_coverage(
    shift_needs: list[ShiftNeed],
    employee_skills: list[EmployeeSkill],
    leave_preferences: list[LeavePreference],
) -> PlanningResult:
    needs = sorted(shift_needs, key=lambda need: (need.date, need.slot, need.role))
    assignments: dict[tuple[str, str, str], tuple[str, ...]] = {}

    for need in needs:
        candidates = [skill for skill in employee_skills if _can_cover(skill, need.role, need.date)]
        ranked = sorted(
            candidates,
            key=lambda skill: (
                1 if _leave_priority(leave_preferences, skill.employee_id, need.date, need.slot) > 0 else 0,
                0 if _prefers_slot(skill, need.slot) else 1,
                len(skill.roles),
                skill.employee_id,
            ),
        )
        assignments[(need.date, need.slot, need.role)] = tuple(
            skill.employee_id for skill in ranked[: need.required_staff]
        )

    gaps = [
        CoverageGap(
            date=need.date,
            slot=need.slot,
            role=need.role,
            required_staff=need.required_staff,
            assigned_employees=assignments[(need.date, need.slot, need.role)],
            missing_count=need.required_staff - len(assignments[(need.date, need.slot, need.role)]),
        )
        for need in needs
        if len(assignments[(need.date, need.slot, need.role)]) < need.required_staff
    ]

    by_employee_slot: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for (date, slot, role), employees in assignments.items():
        for employee_id in employees:
            by_employee_slot[(date, slot, employee_id)].append(role)

    conflicts = sorted(
        (
            EmployeeConflict(
                employee_id=employee_id,
                date=date,
                slot=slot,
                roles=tuple(sorted(set(roles))),
            )
            for (date, slot, employee_id), roles in by_employee_slot.items()
            if len(set(roles)) > 1
        ),
        key=lambda item: (item.date, item.slot, item.employee_id),
    )
    conflict_keys = {(item.date, item.slot, item.employee_id) for item in conflicts}

    assigned_in_slot: dict[tuple[str, str], set[str]] = defaultdict(set)
    for (date, slot, _role), employees in assignments.items():
        assigned_in_slot[(date, slot)].update(employees)

    suggestions: dict[tuple[str, str, str, str, str], SwapSuggestion] = {}
    for need in needs:
        assigned_employees = assignments[(need.date, need.slot, need.role)]
        occupied = assigned_in_slot[(need.date, need.slot)]
        for from_employee in assigned_employees:
            priority = _leave_priority(leave_preferences, from_employee, need.date, need.slot)
            has_conflict = (need.date, need.slot, from_employee) in conflict_keys
            if priority == 0 and not has_conflict:
                continue

            candidates = [
                skill
                for skill in employee_skills
                if skill.employee_id != from_employee
                and _can_cover(skill, need.role, need.date)
                and skill.employee_id not in occupied
                and _leave_priority(leave_preferences, skill.employee_id, need.date, need.slot) == 0
            ]
            ranked_candidates = sorted(
                candidates,
                key=lambda skill: (
                    0 if _prefers_slot(skill, need.slot) else 1,
                    len(skill.roles),
                    skill.employee_id,
                ),
            )
            if not ranked_candidates:
                continue

            replacement = ranked_candidates[0]
            reasons: list[str] = []
            if has_conflict:
                reasons.append("conflict")
            if priority > 0:
                reasons.append("leave")
            if _prefers_slot(replacement, need.slot):
                reasons.append("preferred-slot")

            suggestion = SwapSuggestion(
                date=need.date,
                slot=need.slot,
                role=need.role,
                from_employee=from_employee,
                to_employee=replacement.employee_id,
                score=priority + (3 if has_conflict else 0) + (1 if _prefers_slot(replacement, need.slot) else 0),
                reasons=tuple(reasons),
            )
            suggestions[(suggestion.date, suggestion.slot, suggestion.role, suggestion.from_employee, suggestion.to_employee)] = suggestion

    ordered_suggestions = tuple(
        sorted(
            suggestions.values(),
            key=lambda item: (
                -item.score,
                item.date,
                item.slot,
                item.role,
                item.from_employee,
                item.to_employee,
            ),
        )
    )

    return PlanningResult(
        gaps=tuple(gaps),
        conflicts=tuple(conflicts),
        suggestions=ordered_suggestions,
    )


def _join(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "-"


def render_plan(result: PlanningResult) -> list[str]:
    lines = [
        "SUMMARY",
        f"SUMMARY|{len(result.gaps)}|{len(result.conflicts)}|{len(result.suggestions)}",
        "",
        "GAPS",
    ]
    if result.gaps:
        lines.extend(
            f"GAP|{gap.date}|{gap.slot}|{gap.role}|{gap.required_staff}|{_join(gap.assigned_employees)}|{gap.missing_count}"
            for gap in result.gaps
        )
    else:
        lines.append("GAP|-")

    lines.extend(["", "CONFLICTS"])
    if result.conflicts:
        lines.extend(
            f"CONFLICT|{conflict.employee_id}|{conflict.date}|{conflict.slot}|{_join(conflict.roles)}"
            for conflict in result.conflicts
        )
    else:
        lines.append("CONFLICT|-")

    lines.extend(["", "SUGGESTIONS"])
    if result.suggestions:
        lines.extend(
            f"SWAP|{suggestion.date}|{suggestion.slot}|{suggestion.role}|{suggestion.from_employee}|{suggestion.to_employee}|{suggestion.score}|{_join(suggestion.reasons)}"
            for suggestion in result.suggestions
        )
    else:
        lines.append("SWAP|-")

    return lines


def write_plan(result: PlanningResult, output_path: str) -> None:
    Path(output_path).write_text("\n".join(render_plan(result)) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(
            "Usage: shift_coverage_planner.py <shift_requirements.csv> <employee_skills.csv> <leave_preferences.csv> <output_path>",
            flush=True,
        )
        return 1

    needs = load_shift_needs(argv[1])
    employees = load_employee_skills(argv[2])
    preferences = load_leave_preferences(argv[3])
    result = plan_coverage(needs, employees, preferences)
    write_plan(result, argv[4])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv))
