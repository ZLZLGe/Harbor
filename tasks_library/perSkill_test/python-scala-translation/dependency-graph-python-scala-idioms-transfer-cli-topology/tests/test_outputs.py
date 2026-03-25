#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path("/root")
USER_SCALA_FILE = ROOT / "DependencyPlannerApp.scala"
PROJECT_FIXTURE = ROOT / "scala_dependency_planner"
SAMPLE_INPUT = ROOT / "task_graphs.json"


def _load_source() -> str:
    assert USER_SCALA_FILE.exists(), "Expected /root/DependencyPlannerApp.scala to exist."
    return USER_SCALA_FILE.read_text(encoding="utf-8")


def _prepare_project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "scala_dependency_planner"
    shutil.copytree(
        PROJECT_FIXTURE,
        project_dir,
        ignore=shutil.ignore_patterns("target", "project/target"),
    )
    target_src = project_dir / "src" / "main" / "scala" / "dependencyplanner"
    target_src.mkdir(parents=True, exist_ok=True)
    shutil.copy2(USER_SCALA_FILE, target_src / "DependencyPlannerApp.scala")
    return project_dir


def _run_sbt(project_dir: Path, command: str, timeout: int = 360) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sbt", "-batch", command],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _run_cli(project_dir: Path, payload: dict) -> dict:
    input_path = project_dir / "input.json"
    output_path = project_dir / "output.json"
    input_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = _run_sbt(
        project_dir,
        f"runMain dependencyplanner.DependencyPlannerApp {input_path} {output_path}",
    )
    output = result.stdout + "\n" + result.stderr
    assert result.returncode == 0, output
    assert output_path.exists(), "CLI did not create the requested output file."
    return json.loads(output_path.read_text(encoding="utf-8"))


def _expected_sample_output() -> dict:
    return {
        "reports": [
            {
                "graphId": "release-train",
                "status": "planned",
                "executionOrder": [
                    "lint-config",
                    "compile-core",
                    "package-ui",
                    "ship-bundle",
                    "announce",
                ],
                "cycles": [],
                "unresolved": [],
                "errors": [],
            },
            {
                "graphId": "data-pipeline",
                "status": "planned",
                "executionOrder": [
                    "extract",
                    "reserve-slot",
                    "quality-check",
                    "transform",
                    "publish",
                ],
                "cycles": [],
                "unresolved": [],
                "errors": [],
            },
            {
                "graphId": "ops-drill",
                "status": "cycle",
                "executionOrder": [
                    "bootstrap",
                    "repair",
                ],
                "cycles": [
                    ["audit", "notify"],
                ],
                "unresolved": ["audit", "notify"],
                "errors": [],
            },
            {
                "graphId": "broken-config",
                "status": "invalid",
                "executionOrder": [],
                "cycles": [],
                "unresolved": ["compile", "publish"],
                "errors": [
                    {
                        "kind": "unknown-dependency",
                        "taskId": "compile",
                        "dependencyId": "fetch",
                    },
                    {
                        "kind": "unknown-dependency",
                        "taskId": "publish",
                        "dependencyId": "sign",
                    },
                ],
            },
            {
                "graphId": "duplicate-check",
                "status": "invalid",
                "executionOrder": [],
                "cycles": [],
                "unresolved": ["seed"],
                "errors": [
                    {
                        "kind": "duplicate-task",
                        "taskId": "seed",
                    }
                ],
            },
        ]
    }


def _normalize_report(report: dict) -> dict:
    normalized = dict(report)
    normalized["errors"] = sorted(
        report.get("errors", []),
        key=lambda issue: (
            issue.get("kind", ""),
            issue.get("taskId", ""),
            issue.get("dependencyId", ""),
        ),
    )
    return normalized


def _normalize_reports_payload(payload: dict) -> dict:
    return {
        "reports": sorted(
            (_normalize_report(report) for report in payload.get("reports", [])),
            key=lambda report: report.get("graphId", ""),
        )
    }


def _generate_probe_source() -> str:
    return """package dependencyplanner

object ContractProbe {
  private def expect(condition: Boolean, message: String): Unit =
    if (!condition) throw new IllegalStateException(message)

  private def expectRight[A, B](name: String, value: Either[A, B]): B = value match {
    case Right(result) => result
    case Left(error) => throw new IllegalStateException(s"$name unexpectedly returned Left($error)")
  }

  def main(args: Array[String]): Unit = {
    val releaseGraph = TaskGraph(
      graphId = "release-train",
      tasks = Vector(
        TaskNode("compile-core", Vector.empty, 2),
        TaskNode("lint-config", Vector.empty, 1),
        TaskNode("package-ui", Vector("compile-core"), 1),
        TaskNode("ship-bundle", Vector("package-ui", "lint-config"), 2),
        TaskNode("announce", Vector("ship-bundle"), 3)
      )
    )

    val releaseSnapshot = DependencyPlanner.stableTopologicalOrder(releaseGraph)
    expect(
      releaseSnapshot.executionOrder == Vector("lint-config", "compile-core", "package-ui", "ship-bundle", "announce"),
      "stableTopologicalOrder should preserve deterministic priority/id ordering"
    )
    expect(releaseSnapshot.remaining.isEmpty, "release graph should not have unresolved tasks")

    val cycleGraph = TaskGraph(
      graphId = "ops-drill",
      tasks = Vector(
        TaskNode("bootstrap", Vector.empty, 1),
        TaskNode("notify", Vector("audit"), 2),
        TaskNode("audit", Vector("notify"), 2),
        TaskNode("repair", Vector("bootstrap"), 3)
      )
    )

    val cycleReport = expectRight("cycle plan", DependencyPlanner.plan(cycleGraph))
    expect(cycleReport.status == "cycle", "cycle graph should report cycle status")
    expect(cycleReport.executionOrder == Vector("bootstrap", "repair"), "cycle graph prefix order mismatch")
    expect(cycleReport.cycles == Vector(Vector("audit", "notify")), "cycle graph cycles mismatch")
    expect(cycleReport.unresolved == Vector("audit", "notify"), "cycle graph unresolved mismatch")
    expect(DependencyPlanner.findCycles(cycleGraph, Vector("audit", "notify")) == Vector(Vector("audit", "notify")), "findCycles mismatch")

    val invalidGraph = TaskGraph(
      graphId = "broken-config",
      tasks = Vector(
        TaskNode("seed", Vector.empty, 1),
        TaskNode("seed", Vector.empty, 2),
        TaskNode("publish", Vector("seed", "sign"), 3)
      )
    )

    val issues = DependencyPlanner.plan(invalidGraph) match {
      case Left(found) => found
      case Right(report) => throw new IllegalStateException(s"invalid graph unexpectedly succeeded: $report")
    }

    expect(issues.exists { case DuplicateTask("seed") => true; case _ => false }, "duplicate task issue missing")
    expect(
      issues.exists { case UnknownDependency("publish", "sign") => true; case _ => false },
      "unknown dependency issue missing"
    )

    val parsed = expectRight(
      "fromJson",
      DependencyPlanner.fromJson(
        \"\"\"{"graphs":[{"graphId":"tiny","tasks":[{"id":"a","dependencies":[],"priority":2},{"id":"b","dependencies":["a"],"priority":1}]}]}\"\"\"
      )
    )
    expect(parsed.size == 1, "fromJson should parse one graph")
    expect(parsed.head.tasks.map(_.id) == Vector("a", "b"), "fromJson task ids mismatch")
    expect(DependencyPlanner.planAll(Vector(cycleGraph)).head.status == "cycle", "planAll should preserve cycle status")
    val rendered = ujson.read(DependencyPlanner.renderReports(Vector(cycleReport)))
    expect(rendered("reports").arr.size == 1, "renderReports should emit one report")
    expect(rendered("reports")(0)("graphId").str == "ops-drill", "renderReports output mismatch")

    println("contract probe passed")
  }
}
"""


def test_static_contract_uses_adt_and_typed_errors() -> None:
    source = _load_source()

    assert "package dependencyplanner" in source
    assert re.search(r"sealed\s+(trait|abstract\s+class)\s+PlannerIssue", source)
    assert re.search(r"class\s+DuplicateTask\b", source)
    assert re.search(r"class\s+UnknownDependency\b", source)
    assert re.search(r"object\s+DependencyPlanner\b", source)
    assert re.search(r"object\s+DependencyPlannerApp\b", source)
    assert re.search(r"Either\s*\[", source)
    assert re.search(r"Option\s*\[", source)
    assert re.search(r"\bmatch\s*\{", source)
    assert re.search(r"\bnull\b", source) is None


def test_sample_cli_output_matches_contract(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    payload = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
    observed = _run_cli(project_dir, payload)
    assert _normalize_reports_payload(observed) == _normalize_reports_payload(_expected_sample_output())


def test_contract_probe_passes(tmp_path: Path) -> None:
    project_dir = _prepare_project(tmp_path)
    probe_file = project_dir / "src" / "main" / "scala" / "dependencyplanner" / "ContractProbe.scala"
    probe_file.write_text(_generate_probe_source(), encoding="utf-8")

    compile_result = _run_sbt(project_dir, "compile")
    compile_output = compile_result.stdout + "\n" + compile_result.stderr
    assert compile_result.returncode == 0, compile_output

    probe_result = _run_sbt(project_dir, "runMain dependencyplanner.ContractProbe")
    probe_output = probe_result.stdout + "\n" + probe_result.stderr
    assert probe_result.returncode == 0, probe_output
    assert "contract probe passed" in probe_output
