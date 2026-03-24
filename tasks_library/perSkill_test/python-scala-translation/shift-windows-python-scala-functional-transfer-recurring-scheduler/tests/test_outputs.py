#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


SCALA_FILE = Path("/root/ShiftWindowPlanner.scala")
PYTHON_REFERENCE = Path("/root/ShiftWindowPlanner.py")
CASE_FILE = Path("/root/planner_cases.json")

REQUIRED_PATTERNS = {
    "TimeRange": r"case\s+class\s+TimeRange",
    "ShiftTemplate": r"case\s+class\s+ShiftTemplate",
    "BlockedWindow": r"case\s+class\s+BlockedWindow",
    "PlannerConfig": r"case\s+class\s+PlannerConfig",
    "PlannedShift": r"case\s+class\s+PlannedShift",
    "ShiftWindowPlanner": r"object\s+ShiftWindowPlanner",
    "overlaps": r"def\s+overlaps\s*\(",
    "merge": r"def\s+merge\s*\(",
    "normalized": r"def\s+normalized\s*\(",
    "weekly": r"def\s+weekly\s*\(",
    "withFallbackConfig": r"def\s+withFallbackConfig\s*\(",
    "expandRecurring": r"def\s+expandRecurring\s*\(",
    "filterConflicts": r"def\s+filterConflicts\s*\(",
    "mergeRanges": r"def\s+mergeRanges\s*\(",
    "plan": r"def\s+plan\s*\(",
}

STYLE_PATTERNS = {
    "option": r"Option\[",
    "lazy_sequence": r"(LazyList|Iterator)\[",
    "match": r"\bmatch\s*\{",
    "for_comprehension": r"\bfor\s*[\{\(]",
}


def fail(message: str) -> None:
    print(message)
    sys.exit(1)


def ensure_file(path: Path, label: str) -> str:
    if not path.is_file():
        fail(f"missing {label}: {path}")
    return path.read_text(encoding="utf-8")


def load_reference_module():
    spec = importlib.util.spec_from_file_location("shift_window_reference", PYTHON_REFERENCE)
    if spec is None or spec.loader is None:
        fail(f"unable to load reference module: {PYTHON_REFERENCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def check_source(source: str) -> None:
    if re.search(r"^\s*package\s+\w+", source, re.MULTILINE):
        fail("output file must not declare a package")

    missing = [name for name, pattern in REQUIRED_PATTERNS.items() if not re.search(pattern, source)]
    if missing:
        fail("missing required Scala components: " + ", ".join(missing))

    missing_style = [name for name, pattern in STYLE_PATTERNS.items() if not re.search(pattern, source)]
    if missing_style:
        fail("Scala implementation is missing expected functional patterns: " + ", ".join(missing_style))


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def load_cases() -> dict:
    return json.loads(ensure_file(CASE_FILE, "planner cases"))


def config_from_dict(module, payload: dict | None):
    payload = payload or {}
    required_tags = payload.get("required_tags")
    return module.PlannerConfig(
        merge_gap_minutes=payload.get("merge_gap_minutes"),
        label_prefix=payload.get("label_prefix"),
        required_tags=tuple(required_tags) if required_tags is not None else None,
        max_results=payload.get("max_results"),
        default_repeat_days=payload.get("default_repeat_days"),
    )


def template_from_dict(module, payload: dict):
    return module.ShiftTemplate(
        worker_id=payload["worker_id"],
        window=module.TimeRange(parse_datetime(payload["start"]), parse_datetime(payload["end"])),
        repeat_every_days=payload.get("repeat_every_days"),
        occurrence_count=payload.get("occurrence_count"),
        until=parse_datetime(payload["until"]) if payload.get("until") else None,
        tags=tuple(payload.get("tags", [])),
    )


def blocked_from_dict(module, payload: dict):
    return module.BlockedWindow(
        window=module.TimeRange(parse_datetime(payload["start"]), parse_datetime(payload["end"])),
        worker_id=payload.get("worker_id"),
        reason=payload.get("reason", ""),
    )


def format_dt(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M")


def shift_row(shift) -> str:
    return "|".join(
        [
            shift.worker_id,
            format_dt(shift.window.start),
            format_dt(shift.window.end),
            shift.label,
            ",".join(shift.tags),
        ]
    )


def build_expected(module, cases: dict) -> dict[str, str]:
    defaults = config_from_dict(module, cases["defaults"])
    override = config_from_dict(module, cases["plan_config"])
    normalized = module.ShiftWindowPlanner.with_fallback_config(override, defaults)

    expected = {
        "normalized_gap": str(normalized.merge_gap_minutes),
        "normalized_prefix": normalized.label_prefix or "",
        "normalized_repeat": str(normalized.default_repeat_days),
        "normalized_tag_count": str(len(normalized.required_tags or ())),
        "lazy_before": "0",
        "lazy_after_first": "1",
        "lazy_after_second": "1",
    }

    weekly_case = cases["weekly_case"]
    weekly_template = module.ShiftWindowPlanner.weekly(
        weekly_case["worker_id"],
        parse_datetime(weekly_case["start"]),
        parse_datetime(weekly_case["end"]),
        weekly_case["weeks"],
        weekly_case["tags"],
    )
    weekly_rows = [shift_row(shift) for shift in module.ShiftWindowPlanner.expand_recurring(weekly_template, normalized)]
    expected["weekly_count"] = str(len(weekly_rows))
    expected["weekly_rows"] = ";".join(weekly_rows)

    lazy_template = template_from_dict(module, cases["lazy_templates"][0])
    lazy_iter = module.ShiftWindowPlanner.expand_recurring(lazy_template, normalized)
    expected["lazy_first_start"] = format_dt(next(lazy_iter).window.start)
    expected["lazy_second_start"] = format_dt(next(lazy_iter).window.start)

    first_range = module.TimeRange(parse_datetime("2025-07-01T08:00:00"), parse_datetime("2025-07-01T10:00:00"))
    second_range = module.TimeRange(parse_datetime("2025-07-01T09:30:00"), parse_datetime("2025-07-01T11:00:00"))
    third_range = module.TimeRange(parse_datetime("2025-07-01T11:30:00"), parse_datetime("2025-07-01T12:00:00"))
    expected["overlap_true"] = str(first_range.overlaps(second_range)).lower()
    expected["overlap_false"] = str(first_range.overlaps(third_range)).lower()
    expected["merged_end"] = format_dt(first_range.merge(second_range).end)

    templates = [template_from_dict(module, payload) for payload in cases["plan_templates"]]
    blocked = [blocked_from_dict(module, payload) for payload in cases["blocked"]]
    filtered = list(
        module.ShiftWindowPlanner.filter_conflicts(
            (
                shift
                for template in templates
                for shift in module.ShiftWindowPlanner.expand_recurring(template, normalized)
            ),
            blocked,
        )
    )
    planned = module.ShiftWindowPlanner.plan(templates, blocked, override, defaults)
    expected["filtered_count"] = str(len(filtered))
    expected["plan_count"] = str(len(planned))
    expected["plan_rows"] = ";".join(shift_row(shift) for shift in planned)
    return expected


def scala_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def scala_datetime(value: str) -> str:
    return f"LocalDateTime.parse({scala_string(value)})"


def scala_string_vector(values: list[str]) -> str:
    if not values:
        return "Vector.empty"
    return "Vector(" + ", ".join(scala_string(value) for value in values) + ")"


def scala_option(value, render) -> str:
    if value is None:
        return "None"
    return f"Some({render(value)})"


def scala_config(payload: dict) -> str:
    return "\n    ".join(
        [
            "PlannerConfig(",
            f"mergeGapMinutes = {scala_option(payload.get('merge_gap_minutes'), str)},",
            f"labelPrefix = {scala_option(payload.get('label_prefix'), scala_string)},",
            f"requiredTags = {scala_option(payload.get('required_tags'), scala_string_vector)},",
            f"maxResults = {scala_option(payload.get('max_results'), str)},",
            f"defaultRepeatDays = {scala_option(payload.get('default_repeat_days'), str)}",
            "  )",
        ]
    )


def scala_template(payload: dict) -> str:
    return "\n    ".join(
        [
            "ShiftTemplate(",
            f"workerId = {scala_string(payload['worker_id'])},",
            f"window = TimeRange({scala_datetime(payload['start'])}, {scala_datetime(payload['end'])}),",
            f"repeatEveryDays = {scala_option(payload.get('repeat_every_days'), str)},",
            f"occurrenceCount = {scala_option(payload.get('occurrence_count'), str)},",
            f"until = {scala_option(payload.get('until'), scala_datetime)},",
            f"tags = {scala_string_vector(payload.get('tags', []))}",
            "  )",
        ]
    )


def scala_blocked(payload: dict) -> str:
    return "\n    ".join(
        [
            "BlockedWindow(",
            f"window = TimeRange({scala_datetime(payload['start'])}, {scala_datetime(payload['end'])}),",
            f"workerId = {scala_option(payload.get('worker_id'), scala_string)},",
            f"reason = {scala_string(payload.get('reason', ''))}",
            "  )",
        ]
    )


def build_probe_source(cases: dict) -> str:
    defaults = scala_config(cases["defaults"])
    override = scala_config(cases["plan_config"])
    weekly = cases["weekly_case"]
    lazy_templates = ",\n    ".join(scala_template(payload) for payload in cases["lazy_templates"])
    plan_templates = ",\n    ".join(scala_template(payload) for payload in cases["plan_templates"])
    blocked = ",\n    ".join(scala_blocked(payload) for payload in cases["blocked"])

    return f"""
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

object ShiftWindowPlannerVerifier extends App {{
  private val formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm")

  def fmt(value: LocalDateTime): String =
    value.format(formatter)

  def emit(key: String, value: String): Unit =
    println(s"$key=$value")

  def shiftRow(shift: PlannedShift): String =
    List(
      shift.workerId,
      fmt(shift.window.start),
      fmt(shift.window.end),
      shift.label,
      shift.tags.mkString(",")
    ).mkString("|")

  val defaults =
  {defaults}

  val overrideConfig =
  {override}

  val normalized = ShiftWindowPlanner.withFallbackConfig(Some(overrideConfig), defaults)
  emit("normalized_gap", normalized.mergeGapMinutes.getOrElse(-1).toString)
  emit("normalized_prefix", normalized.labelPrefix.getOrElse(""))
  emit("normalized_repeat", normalized.defaultRepeatDays.getOrElse(-1).toString)
  emit("normalized_tag_count", normalized.requiredTags.getOrElse(Vector.empty).size.toString)

  val weeklyTemplate = ShiftWindowPlanner.weekly(
    {scala_string(weekly["worker_id"])},
    {scala_datetime(weekly["start"])},
    {scala_datetime(weekly["end"])},
    {weekly["weeks"]},
    {scala_string_vector(weekly["tags"])}
  )
  val weeklyRows = ShiftWindowPlanner.expandRecurring(weeklyTemplate, normalized).map(shiftRow).toVector
  emit("weekly_count", weeklyRows.size.toString)
  emit("weekly_rows", weeklyRows.mkString(";"))

  var pulled = 0
  val lazyTemplates = Iterator(
    {lazy_templates}
  ).map {{ template =>
    pulled += 1
    template
  }}
  val lazyExpanded = lazyTemplates.flatMap(template => ShiftWindowPlanner.expandRecurring(template, normalized).iterator)
  emit("lazy_before", pulled.toString)
  val lazyFirst = lazyExpanded.next()
  emit("lazy_after_first", pulled.toString)
  val lazySecond = lazyExpanded.next()
  emit("lazy_after_second", pulled.toString)
  emit("lazy_first_start", fmt(lazyFirst.window.start))
  emit("lazy_second_start", fmt(lazySecond.window.start))

  val firstRange = TimeRange(LocalDateTime.parse("2025-07-01T08:00:00"), LocalDateTime.parse("2025-07-01T10:00:00"))
  val secondRange = TimeRange(LocalDateTime.parse("2025-07-01T09:30:00"), LocalDateTime.parse("2025-07-01T11:00:00"))
  val thirdRange = TimeRange(LocalDateTime.parse("2025-07-01T11:30:00"), LocalDateTime.parse("2025-07-01T12:00:00"))
  emit("overlap_true", firstRange.overlaps(secondRange).toString)
  emit("overlap_false", firstRange.overlaps(thirdRange).toString)
  emit("merged_end", fmt(firstRange.merge(secondRange).end))

  val templates = Vector(
    {plan_templates}
  )
  val blockedWindows = Vector(
    {blocked}
  )

  val filtered = ShiftWindowPlanner.filterConflicts(
    templates.iterator.flatMap(template => ShiftWindowPlanner.expandRecurring(template, normalized).iterator),
    blockedWindows
  ).toVector
  emit("filtered_count", filtered.size.toString)

  val planned = ShiftWindowPlanner.plan(templates, blockedWindows, Some(overrideConfig), defaults)
  emit("plan_count", planned.size.toString)
  emit("plan_rows", planned.map(shiftRow).mkString(";"))
}}
"""


def compile_and_run(source_path: Path, probe_source: str) -> dict[str, str]:
    scalac = shutil.which("scalac")
    scala = shutil.which("scala")
    if not scalac or not scala:
        fail("scala toolchain not found in PATH")

    with tempfile.TemporaryDirectory(prefix="shift-window-verify-") as tmpdir:
        tmp = Path(tmpdir)
        candidate = tmp / "ShiftWindowPlanner.scala"
        verifier = tmp / "Verifier.scala"
        classes = tmp / "classes"
        classes.mkdir()

        candidate.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        verifier.write_text(probe_source, encoding="utf-8")

        compile_proc = subprocess.run(
            [scalac, "-deprecation", "-feature", "-d", str(classes), str(candidate), str(verifier)],
            text=True,
            capture_output=True,
        )
        if compile_proc.returncode != 0:
            fail("scalac failed:\n" + compile_proc.stdout + compile_proc.stderr)

        run_proc = subprocess.run(
            [scala, "-cp", str(classes), "ShiftWindowPlannerVerifier"],
            text=True,
            capture_output=True,
        )
        if run_proc.returncode != 0:
            fail("behavior verification failed:\n" + run_proc.stdout + run_proc.stderr)

        result: dict[str, str] = {}
        for line in run_proc.stdout.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
        return result


def compare_results(expected: dict[str, str], actual: dict[str, str]) -> None:
    missing = [key for key in expected if key not in actual]
    if missing:
        fail("missing verifier outputs: " + ", ".join(sorted(missing)))

    mismatches = [key for key, value in expected.items() if actual.get(key) != value]
    if mismatches:
        details = [f"{key}: expected {expected[key]!r}, got {actual.get(key)!r}" for key in mismatches]
        fail("verifier output mismatch:\n" + "\n".join(details))


def main() -> None:
    source = ensure_file(SCALA_FILE, "Scala output")
    check_source(source)
    module = load_reference_module()
    cases = load_cases()
    expected = build_expected(module, cases)
    probe_source = build_probe_source(cases)
    actual = compile_and_run(SCALA_FILE, probe_source)
    compare_results(expected, actual)
    print("ok")


if __name__ == "__main__":
    main()
