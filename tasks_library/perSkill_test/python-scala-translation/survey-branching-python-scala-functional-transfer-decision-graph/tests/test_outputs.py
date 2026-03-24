#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


SCALA_FILE = Path("/root/SurveyBranching.scala")
PYTHON_REFERENCE = Path("/root/SurveyBranching.py")
CASE_FILE = Path("/root/survey_cases.toml")

REQUIRED_PATTERNS = {
    "PredicateResult": r"case\s+class\s+PredicateResult",
    "ExplanationStep": r"case\s+class\s+ExplanationStep",
    "DecisionResult": r"case\s+class\s+DecisionResult",
    "SurveyNode": r"sealed\s+trait\s+SurveyNode",
    "OutcomeNode": r"case\s+class\s+OutcomeNode",
    "BranchCase": r"case\s+class\s+BranchCase",
    "BranchNode": r"case\s+class\s+BranchNode",
    "SurveyBranching": r"object\s+SurveyBranching",
    "answerEquals": r"def\s+answerEquals\s*\(",
    "answerIn": r"def\s+answerIn\s*\(",
    "numericAtLeast": r"def\s+numericAtLeast\s*\(",
    "allOf": r"def\s+allOf\s*\(",
    "anyOf": r"def\s+anyOf\s*\(",
    "evaluate": r"def\s+evaluate\s*\(",
    "reachableSegments": r"def\s+reachableSegments\s*\(",
    "renderExplanation": r"def\s+renderExplanation\s*\(",
}

STYLE_PATTERNS = {
    "option": r"Option\[",
    "vector": r"Vector\[",
    "match": r"\bmatch\s*\{",
    "function_type": r"=>",
}


def fail(message: str) -> None:
    print(message)
    sys.exit(1)


def ensure_text(path: Path, label: str) -> str:
    if not path.is_file():
        fail(f"missing {label}: {path}")
    return path.read_text(encoding="utf-8")


def load_reference_module():
    spec = importlib.util.spec_from_file_location("survey_branching_reference", PYTHON_REFERENCE)
    if spec is None or spec.loader is None:
        fail(f"unable to load reference module: {PYTHON_REFERENCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_cases() -> dict:
    return tomllib.loads(ensure_text(CASE_FILE, "survey cases"))


def check_source(source: str) -> None:
    if re.search(r"^\s*package\s+\w+", source, re.MULTILINE):
        fail("output file must not declare a package")

    missing = [name for name, pattern in REQUIRED_PATTERNS.items() if not re.search(pattern, source)]
    if missing:
        fail("missing required Scala components: " + ", ".join(missing))

    missing_style = [name for name, pattern in STYLE_PATTERNS.items() if not re.search(pattern, source)]
    if missing_style:
        fail("Scala implementation is missing expected functional patterns: " + ", ".join(missing_style))


def build_graph(module, cases: dict):
    intensive = cases["thresholds"]["intensive_hours"]
    departments = set(cases["rules"]["engineering_departments"])

    workshop = module.OutcomeNode("live-workshop", "Interactive certification workshop")
    handbook = module.OutcomeNode("cert-handbook", "Self-serve certification handbook")
    student_basics = module.OutcomeNode("student-basics", "General student onboarding")
    student_accelerated = module.OutcomeNode("accelerated-coaching", "High-intensity student coaching")
    student_guides = module.OutcomeNode("self-paced-guides", "Part-time study guide path")
    operations_review = module.OutcomeNode("operations-review", "Operations review checklist")
    general = module.OutcomeNode("general-onboarding", "Generic onboarding checklist")

    cert_branch = module.BranchNode(
        node_id="cert-format",
        cases=(
            module.BranchCase(
                label="interactive",
                predicate=module.SurveyBranching.answer_equals("prefers_workshop", True),
                next_node=workshop,
            ),
        ),
        default_next=handbook,
        default_label="self-serve",
    )

    student_branch = module.BranchNode(
        node_id="study-profile",
        cases=(
            module.BranchCase(
                label="intensive-learning",
                predicate=module.SurveyBranching.all_of(
                    module.SurveyBranching.answer_equals("study_mode", "full_time"),
                    module.SurveyBranching.numeric_at_least("weekly_hours", intensive),
                ),
                next_node=student_accelerated,
            ),
            module.BranchCase(
                label="part-time-guides",
                predicate=module.SurveyBranching.answer_equals("study_mode", "part_time"),
                next_node=student_guides,
            ),
        ),
        default_next=student_basics,
        default_label="core-student",
    )

    professional_branch = module.BranchNode(
        node_id="career-track",
        cases=(
            module.BranchCase(
                label="cert-path",
                predicate=module.SurveyBranching.any_of(
                    module.SurveyBranching.answer_in("department", departments),
                    module.SurveyBranching.answer_equals("needs_certification", True),
                ),
                next_node=cert_branch,
            ),
        ),
        default_next=operations_review,
        default_label="ops-review",
    )

    return module.BranchNode(
        node_id="entry",
        cases=(
            module.BranchCase(
                label="student-track",
                predicate=module.SurveyBranching.answer_equals("role", "student"),
                next_node=student_branch,
            ),
            module.BranchCase(
                label="professional-track",
                predicate=module.SurveyBranching.answer_equals("role", "professional"),
                next_node=professional_branch,
            ),
        ),
        default_next=general,
        default_label="general-track",
    )


def build_expected(module, cases: dict) -> dict[str, str]:
    root = build_graph(module, cases)
    expected = {
        "reachable_segments": ",".join(module.SurveyBranching.reachable_segments(root)),
    }
    for name, payload in cases["scenarios"].items():
        result = module.SurveyBranching.evaluate(root, payload)
        expected[f"{name}_segment"] = result.segment or ""
        expected[f"{name}_missing"] = ",".join(result.missing_answers)
        expected[f"{name}_resolved"] = str(result.is_resolved()).lower()
        expected[f"{name}_explanation"] = module.SurveyBranching.render_explanation(result)
    return expected


def scala_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def scala_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return scala_string(str(value))


def scala_map(payload: dict[str, object]) -> str:
    if not payload:
        return "Map.empty[String, Any]"
    entries = ", ".join(f"{scala_string(key)} -> {scala_value(value)}" for key, value in payload.items())
    return f"Map[String, Any]({entries})"


def build_probe_source(cases: dict) -> str:
    intensive = cases["thresholds"]["intensive_hours"]
    departments = ", ".join(scala_string(value) for value in cases["rules"]["engineering_departments"])
    scenario_calls = "\n".join(
        [
            f'  record("{name}", {scala_map(payload)})'
            for name, payload in cases["scenarios"].items()
        ]
    )

    return f"""
object SurveyBranchingVerifier extends App {{
  def emit(key: String, value: String): Unit =
    println(s"$key=$value")

  val root =
    BranchNode(
      nodeId = "entry",
      cases = Vector(
        BranchCase(
          label = "student-track",
          predicate = SurveyBranching.answerEquals("role", "student"),
          nextNode = BranchNode(
            nodeId = "study-profile",
            cases = Vector(
              BranchCase(
                label = "intensive-learning",
                predicate = SurveyBranching.allOf(
                  SurveyBranching.answerEquals("study_mode", "full_time"),
                  SurveyBranching.numericAtLeast("weekly_hours", BigDecimal("{intensive}"))
                ),
                nextNode = OutcomeNode("accelerated-coaching", "High-intensity student coaching")
              ),
              BranchCase(
                label = "part-time-guides",
                predicate = SurveyBranching.answerEquals("study_mode", "part_time"),
                nextNode = OutcomeNode("self-paced-guides", "Part-time study guide path")
              )
            ),
            defaultNext = Some(OutcomeNode("student-basics", "General student onboarding")),
            defaultLabel = "core-student"
          )
        ),
        BranchCase(
          label = "professional-track",
          predicate = SurveyBranching.answerEquals("role", "professional"),
          nextNode = BranchNode(
            nodeId = "career-track",
            cases = Vector(
              BranchCase(
                label = "cert-path",
                predicate = SurveyBranching.anyOf(
                  SurveyBranching.answerIn("department", Set({departments})),
                  SurveyBranching.answerEquals("needs_certification", true)
                ),
                nextNode = BranchNode(
                  nodeId = "cert-format",
                  cases = Vector(
                    BranchCase(
                      label = "interactive",
                      predicate = SurveyBranching.answerEquals("prefers_workshop", true),
                      nextNode = OutcomeNode("live-workshop", "Interactive certification workshop")
                    )
                  ),
                  defaultNext = Some(OutcomeNode("cert-handbook", "Self-serve certification handbook")),
                  defaultLabel = "self-serve"
                )
              )
            ),
            defaultNext = Some(OutcomeNode("operations-review", "Operations review checklist")),
            defaultLabel = "ops-review"
          )
        )
      ),
      defaultNext = Some(OutcomeNode("general-onboarding", "Generic onboarding checklist")),
      defaultLabel = "general-track"
    )

  emit("reachable_segments", SurveyBranching.reachableSegments(root).mkString(","))

  def record(name: String, answers: Map[String, Any]): Unit = {{
    val result = SurveyBranching.evaluate(root, answers)
    emit(s"${{name}}_segment", result.segment.getOrElse(""))
    emit(s"${{name}}_missing", result.missingAnswers.mkString(","))
    emit(s"${{name}}_resolved", result.isResolved.toString)
    emit(s"${{name}}_explanation", SurveyBranching.renderExplanation(result))
  }}

{scenario_calls}
}}
"""


def run_probe(probe_source: str) -> dict[str, str]:
    scalac = shutil.which("scalac")
    scala = shutil.which("scala")
    if not scalac or not scala:
        fail("scala toolchain not found in PATH")

    with tempfile.TemporaryDirectory(prefix="survey-branching-verify-") as tmpdir:
        tmp = Path(tmpdir)
        candidate = tmp / "SurveyBranching.scala"
        verifier = tmp / "Verifier.scala"
        classes = tmp / "classes"
        classes.mkdir()

        candidate.write_text(ensure_text(SCALA_FILE, "Scala output"), encoding="utf-8")
        verifier.write_text(probe_source, encoding="utf-8")

        compile_proc = subprocess.run(
            [scalac, "-deprecation", "-feature", "-d", str(classes), str(candidate), str(verifier)],
            text=True,
            capture_output=True,
        )
        if compile_proc.returncode != 0:
            fail("scalac failed:\n" + compile_proc.stdout + compile_proc.stderr)

        run_proc = subprocess.run(
            [scala, "-cp", str(classes), "SurveyBranchingVerifier"],
            text=True,
            capture_output=True,
        )
        if run_proc.returncode != 0:
            fail("behavior verification failed:\n" + run_proc.stdout + run_proc.stderr)

        observed: dict[str, str] = {}
        for line in run_proc.stdout.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            observed[key.strip()] = value.strip()
        return observed


def compare(expected: dict[str, str], observed: dict[str, str]) -> None:
    missing_keys = [key for key in expected if key not in observed]
    if missing_keys:
        fail("probe output missing keys: " + ", ".join(missing_keys))

    mismatches = []
    for key, expected_value in expected.items():
        if observed.get(key) != expected_value:
            mismatches.append(f"{key}: expected {expected_value!r}, got {observed.get(key)!r}")
    if mismatches:
        fail("probe mismatches:\n" + "\n".join(mismatches))


def main() -> None:
    source = ensure_text(SCALA_FILE, "Scala output")
    check_source(source)
    module = load_reference_module()
    cases = load_cases()
    expected = build_expected(module, cases)
    observed = run_probe(build_probe_source(cases))
    compare(expected, observed)
    print("ok")


if __name__ == "__main__":
    main()
