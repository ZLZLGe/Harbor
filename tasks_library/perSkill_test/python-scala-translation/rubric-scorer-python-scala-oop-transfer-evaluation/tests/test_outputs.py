#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_PATTERNS: list[tuple[str, str]] = [
    ("package", r"package\s+rubric"),
    ("RubricQuestion", r"(case\s+class|class)\s+RubricQuestion"),
    ("RubricQuestionObject", r"object\s+RubricQuestion"),
    ("ScoreResult", r"(case\s+class|class)\s+ScoreResult"),
    ("ScoreResultObject", r"object\s+ScoreResult"),
    ("SubmissionReport", r"(case\s+class|class)\s+SubmissionReport"),
    ("SubmissionReportObject", r"object\s+SubmissionReport"),
    ("AbstractScorer", r"abstract\s+class\s+AbstractScorer"),
    ("TextRubricScorer", r"class\s+TextRubricScorer"),
    ("NumericRubricScorer", r"class\s+NumericRubricScorer"),
    ("WeightedRubricScorer", r"class\s+WeightedRubricScorer"),
    ("BatchRubricScorer", r"class\s+BatchRubricScorer"),
    ("BatchRubricScorerObject", r"object\s+BatchRubricScorer"),
    ("fromPayload", r"def\s+fromPayload"),
    ("fromEvaluation", r"def\s+fromEvaluation"),
    ("withMetadata", r"def\s+withMetadata"),
    ("scoreRaw", r"def\s+scoreRaw"),
    ("buildResult", r"def\s+buildResult"),
    ("scoreSubmission", r"def\s+scoreSubmission"),
    ("scoreAll", r"def\s+scoreAll"),
    ("averageRatio", r"def\s+averageRatio"),
    ("render", r"def\s+render"),
]

ANTI_PATTERNS: list[tuple[str, str]] = [
    (r"\bnull\b", "不要使用 null"),
    (r"\.asInstanceOf\[", "不要使用 asInstanceOf"),
]


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def load_module(source_file: Path):
    spec = importlib.util.spec_from_file_location("rubric_scorer_source", source_file)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载 Python 参考实现: {source_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_rows(csv_file: Path) -> list[dict[str, str]]:
    with csv_file.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def parse_output(stdout: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key] = value
    return parsed


def format_num(value: float) -> str:
    return f"{value:.4f}"


def scala_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def build_expected(module, rows: list[dict[str, str]]) -> dict[str, str]:
    question_thesis = module.RubricQuestion.from_payload(
        {
            "question_id": "thesis",
            "prompt": "State the claim and cite evidence",
            "max_points": 4,
            "weight": 1.0,
            "keywords": ["Claim", "Evidence"],
            "metadata": {"topic": "writing"},
        }
    )
    question_estimate = module.RubricQuestion.from_payload(
        {
            "question_id": "estimate",
            "prompt": "Approximate pi",
            "max_points": 3,
            "weight": 1.5,
            "metadata": {"topic": "math"},
        }
    )
    question_carbon = module.RubricQuestion.from_payload(
        {
            "question_id": "carbon",
            "prompt": "Mention carbon and the number of reservoirs",
            "max_points": 5,
            "weight": 2.0,
            "keywords": ["carbon", "reservoir"],
            "metadata": {"topic": "science"},
        }
    )

    text_scorer = module.TextRubricScorer(min_length=12, bonus_points=0.5)
    numeric_scorer = module.NumericRubricScorer(target=3.14, tolerance=0.05, partial_credit=0.4)
    weighted_scorer = module.WeightedRubricScorer(
        [
            ("text", module.TextRubricScorer(min_length=10), 0.6),
            ("numeric", module.NumericRubricScorer(target=2.0, tolerance=0.1, partial_credit=0.5), 0.4),
        ]
    )

    sample_text = text_scorer.build_result(
        question_thesis,
        rows[0]["thesis"],
        mode="single",
    ).with_metadata(reviewer="mentor")
    sample_numeric = numeric_scorer.score(question_estimate, rows[1]["estimate"])
    sample_weighted = weighted_scorer.build_result(question_carbon, rows[2]["carbon"], source="mixed")

    batch = module.BatchRubricScorer(
        [question_thesis, question_estimate, question_carbon],
        {
            "thesis": text_scorer,
            "estimate": numeric_scorer,
            "carbon": weighted_scorer,
        },
        cohort_name="sec-a",
    )
    submissions = [
        (row["student_id"], {key: value for key, value in row.items() if key != "student_id"})
        for row in rows
    ]
    reports = batch.score_all(submissions)
    ordered_reports = "|".join(report.render() for report in reports)
    top_student = max(reports, key=lambda report: (report.total_weighted_score, report.student_id)).student_id

    return {
        "question.keywords": ",".join(question_thesis.keywords),
        "question.weight": format_num(question_estimate.weight),
        "text.render": sample_text.render(),
        "text.mode": sample_text.metadata["mode"],
        "text.reviewer": sample_text.metadata["reviewer"],
        "numeric.feedback": sample_numeric.feedback,
        "numeric.raw": format_num(sample_numeric.raw_score),
        "numeric.weighted": format_num(sample_numeric.weighted_score),
        "weighted.feedback": sample_weighted.feedback,
        "weighted.summary": sample_weighted.metadata["component_summary"],
        "weighted.count": sample_weighted.metadata["component_count"],
        "report.first": reports[0].render(),
        "report.last": reports[-1].render(),
        "report.average": format_num(batch.average_ratio(reports)),
        "report.top_student": top_student,
        "report.lines": ordered_reports,
    }


def build_runner(rows: list[dict[str, str]]) -> str:
    row_literals = []
    for row in rows:
        row_literals.append(
            "      "
            + f'({scala_string(row["student_id"])}, Map('
            + ", ".join(
                f'{scala_string(key)} -> {scala_string(value)}'
                for key, value in row.items()
                if key != "student_id"
            )
            + ")),"
        )

    return f"""import rubric._

object TestRunner {{
  private def line(key: String, value: String): Unit = println(s"$key=$value")

  private def formatNum(value: Double): String = f"$value%.4f"

  def main(args: Array[String]): Unit = {{
    val questionThesis = RubricQuestion.fromPayload(
      Map(
        "question_id" -> "thesis",
        "prompt" -> "State the claim and cite evidence",
        "max_points" -> 4,
        "weight" -> 1.0,
        "keywords" -> Vector("Claim", "Evidence"),
        "metadata" -> Map("topic" -> "writing")
      )
    )
    val questionEstimate = RubricQuestion.fromPayload(
      Map(
        "question_id" -> "estimate",
        "prompt" -> "Approximate pi",
        "max_points" -> 3,
        "weight" -> 1.5,
        "metadata" -> Map("topic" -> "math")
      )
    )
    val questionCarbon = RubricQuestion.fromPayload(
      Map(
        "question_id" -> "carbon",
        "prompt" -> "Mention carbon and the number of reservoirs",
        "max_points" -> 5,
        "weight" -> 2.0,
        "keywords" -> Vector("carbon", "reservoir"),
        "metadata" -> Map("topic" -> "science")
      )
    )

    val textScorer = new TextRubricScorer(minLength = 12, bonusPoints = 0.5)
    val numericScorer = new NumericRubricScorer(target = 3.14, tolerance = 0.05, partialCredit = 0.4)
    val weightedScorer = new WeightedRubricScorer(
      Vector(
        ("text", new TextRubricScorer(minLength = 10), 0.6),
        ("numeric", new NumericRubricScorer(target = 2.0, tolerance = 0.1, partialCredit = 0.5), 0.4)
      )
    )

    val sampleText = textScorer
      .buildResult(questionThesis, {scala_string(rows[0]["thesis"])}, "mode" -> "single")
      .withMetadata("reviewer" -> "mentor")
    val sampleNumeric = numericScorer.score(questionEstimate, {scala_string(rows[1]["estimate"])})
    val sampleWeighted = weightedScorer.buildResult(questionCarbon, {scala_string(rows[2]["carbon"])}, "source" -> "mixed")

    val batch = BatchRubricScorer(
      Vector(questionThesis, questionEstimate, questionCarbon),
      Map(
        "thesis" -> textScorer,
        "estimate" -> numericScorer,
        "carbon" -> weightedScorer
      ),
      cohortName = "sec-a"
    )

    val submissions = Vector(
{chr(10).join(row_literals)}
    )

    val reports = batch.scoreAll(submissions)
    val topStudent = reports.maxBy(report => (report.totalWeightedScore, report.studentId)).studentId

    line("question.keywords", questionThesis.keywords.mkString(","))
    line("question.weight", formatNum(questionEstimate.weight))
    line("text.render", sampleText.render)
    line("text.mode", sampleText.metadata("mode"))
    line("text.reviewer", sampleText.metadata("reviewer"))
    line("numeric.feedback", sampleNumeric.feedback)
    line("numeric.raw", formatNum(sampleNumeric.rawScore))
    line("numeric.weighted", formatNum(sampleNumeric.weightedScore))
    line("weighted.feedback", sampleWeighted.feedback)
    line("weighted.summary", sampleWeighted.metadata("component_summary"))
    line("weighted.count", sampleWeighted.metadata("component_count"))
    line("report.first", reports.head.render)
    line("report.last", reports.last.render)
    line("report.average", formatNum(batch.averageRatio(reports)))
    line("report.top_student", topStudent)
    line("report.lines", reports.map(_.render).mkString("|"))
  }}
}}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scala_file")
    parser.add_argument("source_file")
    parser.add_argument("csv_file")
    args = parser.parse_args()

    scala_file = Path(args.scala_file)
    source_file = Path(args.source_file)
    csv_file = Path(args.csv_file)

    if not source_file.exists():
        raise SystemExit(f"缺少输入资产: {source_file}")
    if not csv_file.exists():
        raise SystemExit(f"缺少输入资产: {csv_file}")
    if not scala_file.exists():
        raise SystemExit(f"缺少输出文件: {scala_file}")

    source = scala_file.read_text(encoding="utf-8")
    for name, pattern in REQUIRED_PATTERNS:
        if re.search(pattern, source) is None:
            raise SystemExit(f"缺少必需实现: {name}")

    for pattern, message in ANTI_PATTERNS:
        if re.search(pattern, source):
            raise SystemExit(message)

    if shutil.which("scalac") is None or run(["scalac", "-version"]).returncode != 0:
        raise SystemExit("scalac 不可用")
    if shutil.which("scala") is None or run(["scala", "-version"]).returncode != 0:
        raise SystemExit("scala 不可用")

    module = load_module(source_file)
    rows = read_rows(csv_file)
    expected = build_expected(module, rows)
    runner_source = build_runner(rows)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        runner_file = tmp_path / "TestRunner.scala"
        runner_file.write_text(runner_source, encoding="utf-8")

        compile_result = run(["scalac", "-d", str(out_dir), str(scala_file), str(runner_file)])
        if compile_result.returncode != 0:
            raise SystemExit(
                "Scala 编译失败:\n"
                f"{compile_result.stdout}\n{compile_result.stderr}".strip()
            )

        test_result = run(["scala", "-cp", str(out_dir), "TestRunner"])
        if test_result.returncode != 0:
            raise SystemExit(
                "语义校验失败:\n"
                f"{test_result.stdout}\n{test_result.stderr}".strip()
            )

        actual = parse_output(test_result.stdout)

    missing = sorted(set(expected) - set(actual))
    if missing:
        raise SystemExit(f"Scala 测试输出缺少字段: {', '.join(missing)}")

    mismatches = [
        f"{key}: expected={expected[key]!r} actual={actual[key]!r}"
        for key in sorted(expected)
        if expected[key] != actual.get(key)
    ]
    if mismatches:
        raise SystemExit("输出与参考实现不一致:\n" + "\n".join(mismatches))

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
