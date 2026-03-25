from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path


SCALA_FILE = Path("/root/ShiftCoveragePlanner.scala")
PYTHON_REFERENCE = Path("/root/shift_coverage_planner.py")
DEFAULT_SHIFT_REQUIREMENTS = Path("/root/shift_requirements.csv")
DEFAULT_EMPLOYEE_SKILLS = Path("/root/employee_skills.csv")
DEFAULT_LEAVE_PREFERENCES = Path("/root/leave_preferences.csv")

HARNESS_SOURCE = textwrap.dedent(
    """
    import ShiftCoveragePlanner._

    object ShiftCoverageHarness {
      def main(args: Array[String]): Unit = {
        val shiftNeeds = loadShiftNeeds(args(0))
        val employeeSkills = loadEmployeeSkills(args(1))
        val leavePreferences = loadLeavePreferences(args(2))
        val result = planCoverage(shiftNeeds, employeeSkills, leavePreferences)

        println(s"COUNTS|${result.gaps.size}|${result.conflicts.size}|${result.suggestions.size}")
        result.gaps.foreach { gap =>
          val employees = if (gap.assignedEmployees.isEmpty) "-" else gap.assignedEmployees.mkString(",")
          println(s"GAP|${gap.date}|${gap.slot}|${gap.role}|${gap.requiredStaff}|${employees}|${gap.missingCount}")
        }
        result.conflicts.foreach { conflict =>
          val roles = if (conflict.roles.isEmpty) "-" else conflict.roles.mkString(",")
          println(s"CONFLICT|${conflict.employeeId}|${conflict.date}|${conflict.slot}|${roles}")
        }
        result.suggestions.foreach { suggestion =>
          val reasons = if (suggestion.reasons.isEmpty) "-" else suggestion.reasons.mkString(",")
          println(
            s"SWAP|${suggestion.date}|${suggestion.slot}|${suggestion.role}|${suggestion.fromEmployee}|${suggestion.toEmployee}|${suggestion.score}|${reasons}"
          )
        }
        println("RENDERED")
        renderPlan(result).foreach(println)
      }
    }
    """
)


def load_reference_module():
    spec = importlib.util.spec_from_file_location("shift_coverage_planner_ref", PYTHON_REFERENCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compile_scala(build_dir: Path) -> None:
    assert SCALA_FILE.exists(), "缺少 /root/ShiftCoveragePlanner.scala"
    source_text = SCALA_FILE.read_text(encoding="utf-8")
    assert "package " not in source_text, "不应包含 package 声明"

    harness_file = build_dir / "ShiftCoverageHarness.scala"
    harness_file.write_text(HARNESS_SOURCE, encoding="utf-8")

    compile_proc = subprocess.run(
        ["scalac", "-d", str(build_dir), str(SCALA_FILE), str(harness_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert compile_proc.returncode == 0, compile_proc.stderr or compile_proc.stdout


def run_cli(
    build_dir: Path,
    shift_requirements: Path,
    employee_skills: Path,
    leave_preferences: Path,
    output_path: Path,
) -> str:
    run_proc = subprocess.run(
        [
            "scala",
            "-cp",
            str(build_dir),
            "ShiftCoveragePlanner",
            str(shift_requirements),
            str(employee_skills),
            str(leave_preferences),
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run_proc.returncode == 0, run_proc.stderr or run_proc.stdout
    return output_path.read_text(encoding="utf-8")


def run_harness(
    build_dir: Path,
    shift_requirements: Path,
    employee_skills: Path,
    leave_preferences: Path,
) -> list[str]:
    run_proc = subprocess.run(
        [
            "scala",
            "-cp",
            str(build_dir),
            "ShiftCoverageHarness",
            str(shift_requirements),
            str(employee_skills),
            str(leave_preferences),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run_proc.returncode == 0, run_proc.stderr or run_proc.stdout
    return [line.strip() for line in run_proc.stdout.splitlines()]


def expected_rendered(module, shift_requirements: Path, employee_skills: Path, leave_preferences: Path) -> str:
    needs = module.load_shift_needs(str(shift_requirements))
    employees = module.load_employee_skills(str(employee_skills))
    preferences = module.load_leave_preferences(str(leave_preferences))
    result = module.plan_coverage(needs, employees, preferences)
    return "\n".join(module.render_plan(result)) + "\n"


def expected_harness_lines(module, shift_requirements: Path, employee_skills: Path, leave_preferences: Path) -> list[str]:
    needs = module.load_shift_needs(str(shift_requirements))
    employees = module.load_employee_skills(str(employee_skills))
    preferences = module.load_leave_preferences(str(leave_preferences))
    result = module.plan_coverage(needs, employees, preferences)

    lines = [f"COUNTS|{len(result.gaps)}|{len(result.conflicts)}|{len(result.suggestions)}"]
    lines.extend(
        f"GAP|{gap.date}|{gap.slot}|{gap.role}|{gap.required_staff}|{','.join(gap.assigned_employees) if gap.assigned_employees else '-'}|{gap.missing_count}"
        for gap in result.gaps
    )
    lines.extend(
        f"CONFLICT|{conflict.employee_id}|{conflict.date}|{conflict.slot}|{','.join(conflict.roles) if conflict.roles else '-'}"
        for conflict in result.conflicts
    )
    lines.extend(
        f"SWAP|{suggestion.date}|{suggestion.slot}|{suggestion.role}|{suggestion.from_employee}|{suggestion.to_employee}|{suggestion.score}|{','.join(suggestion.reasons) if suggestion.reasons else '-'}"
        for suggestion in result.suggestions
    )
    lines.append("RENDERED")
    lines.extend(module.render_plan(result))
    return lines


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_shift_coverage_planner_matches_reference_on_default_and_custom_inputs(tmp_path: Path):
    module = load_reference_module()
    build_dir = tmp_path / "scala-build"
    build_dir.mkdir()
    compile_scala(build_dir)

    default_output = tmp_path / "default-plan.txt"
    actual_default = run_cli(
        build_dir,
        DEFAULT_SHIFT_REQUIREMENTS,
        DEFAULT_EMPLOYEE_SKILLS,
        DEFAULT_LEAVE_PREFERENCES,
        default_output,
    )
    assert actual_default == expected_rendered(
        module,
        DEFAULT_SHIFT_REQUIREMENTS,
        DEFAULT_EMPLOYEE_SKILLS,
        DEFAULT_LEAVE_PREFERENCES,
    )
    assert run_harness(
        build_dir,
        DEFAULT_SHIFT_REQUIREMENTS,
        DEFAULT_EMPLOYEE_SKILLS,
        DEFAULT_LEAVE_PREFERENCES,
    ) == expected_harness_lines(
        module,
        DEFAULT_SHIFT_REQUIREMENTS,
        DEFAULT_EMPLOYEE_SKILLS,
        DEFAULT_LEAVE_PREFERENCES,
    )

    custom_shift_requirements = tmp_path / "custom_shift_requirements.csv"
    custom_employee_skills = tmp_path / "custom_employee_skills.csv"
    custom_leave_preferences = tmp_path / "custom_leave_preferences.csv"
    custom_output = tmp_path / "custom-plan.txt"

    write_csv(
        custom_shift_requirements,
        ["date", "slot", "role", "required_staff"],
        [
            {"date": "2026-05-10", "slot": "morning", "role": "greeter", "required_staff": "1"},
            {"date": "2026-05-10", "slot": "morning", "role": "cashier", "required_staff": "1"},
            {"date": "2026-05-10", "slot": "evening", "role": "stock", "required_staff": "2"},
            {"date": "2026-05-11", "slot": "mid", "role": "cashier", "required_staff": "2"},
        ],
    )
    write_csv(
        custom_employee_skills,
        ["employee_id", "roles", "preferred_slots", "unavailable_dates"],
        [
            {"employee_id": "A01", "roles": "greeter|cashier", "preferred_slots": "morning", "unavailable_dates": ""},
            {"employee_id": "A02", "roles": "cashier|stock", "preferred_slots": "mid", "unavailable_dates": ""},
            {"employee_id": "A03", "roles": "stock", "preferred_slots": "evening", "unavailable_dates": ""},
            {"employee_id": "A04", "roles": "stock|greeter", "preferred_slots": "morning|evening", "unavailable_dates": "2026-05-11"},
            {"employee_id": "A05", "roles": "cashier", "preferred_slots": "mid", "unavailable_dates": "2026-05-10"},
        ],
    )
    write_csv(
        custom_leave_preferences,
        ["employee_id", "date", "avoid_slots", "priority", "note"],
        [
            {"employee_id": "A01", "date": "2026-05-10", "avoid_slots": "morning", "priority": "4", "note": "training"},
            {"employee_id": "A02", "date": "2026-05-10", "avoid_slots": "evening", "priority": "2", "note": "pickup"},
            {"employee_id": "A05", "date": "2026-05-11", "avoid_slots": "mid", "priority": "5", "note": "exam"},
        ],
    )

    actual_custom = run_cli(
        build_dir,
        custom_shift_requirements,
        custom_employee_skills,
        custom_leave_preferences,
        custom_output,
    )
    assert actual_custom == expected_rendered(
        module,
        custom_shift_requirements,
        custom_employee_skills,
        custom_leave_preferences,
    )
    assert run_harness(
        build_dir,
        custom_shift_requirements,
        custom_employee_skills,
        custom_leave_preferences,
    ) == expected_harness_lines(
        module,
        custom_shift_requirements,
        custom_employee_skills,
        custom_leave_preferences,
    )
