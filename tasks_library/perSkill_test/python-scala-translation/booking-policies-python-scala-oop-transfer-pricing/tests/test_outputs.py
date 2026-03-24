#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_PATTERNS: list[tuple[str, str]] = [
    ("package", r"package\s+booking"),
    ("RoomType", r"(case\s+class|class)\s+RoomType"),
    ("BookingOrder", r"(case\s+class|class)\s+BookingOrder"),
    ("ChargeSummary", r"(case\s+class|class)\s+ChargeSummary"),
    ("DiscountPolicy", r"abstract\s+class\s+DiscountPolicy"),
    ("StandardPolicy", r"class\s+StandardPolicy"),
    ("MemberPolicy", r"class\s+MemberPolicy"),
    ("CorporatePolicy", r"class\s+CorporatePolicy"),
    ("LongStayPolicy", r"class\s+LongStayPolicy"),
    ("FamilyPolicy", r"class\s+FamilyPolicy"),
    ("PolicyRegistry", r"object\s+PolicyRegistry"),
    ("PricingLedger", r"(case\s+class|class)\s+PricingLedger"),
    ("PricingLedgerObject", r"object\s+PricingLedger"),
    ("fromCode", r"def\s+fromCode"),
    ("fromPayload", r"def\s+fromPayload"),
    ("renderLine", r"def\s+renderLine"),
    ("quote", r"def\s+quote"),
    ("quoteAll", r"def\s+quoteAll"),
    ("register", r"def\s+register"),
    ("buildDefaults", r"def\s+buildDefaults"),
    ("supportedCodes", r"def\s+supportedCodes"),
    ("fromPayloads", r"def\s+fromPayloads"),
    ("totalDue", r"def\s+totalDue"),
    ("totalDiscount", r"def\s+totalDiscount"),
    ("renderReport", r"def\s+renderReport"),
]

ANTI_PATTERNS: list[tuple[str, str]] = [
    (r"\bnull\b", "不要使用 null"),
    (r"\.asInstanceOf\[", "不要使用 asInstanceOf"),
]


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def load_module(source_file: Path):
    spec = importlib.util.spec_from_file_location("booking_policies_source", source_file)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载 Python 参考实现: {source_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_output(stdout: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key] = value
    return parsed


def to_scala(value: object) -> str:
    if isinstance(value, str):
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )
        return f'"{escaped}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return f"Vector({', '.join(to_scala(item) for item in value)})"
    if isinstance(value, dict):
        items = ", ".join(f"{to_scala(key)} -> {to_scala(item)}" for key, item in value.items())
        return f"Map({items})"
    raise TypeError(f"不支持的 Scala 字面量类型: {type(value)!r}")


def build_expected(module, scenarios: dict[str, object]) -> dict[str, str]:
    expected: dict[str, str] = {}
    expected["supported_codes"] = ",".join(module.PolicyRegistry.supported_codes())

    for item in scenarios["matrix"]:
        label = item["label"]
        payload = item["payload"]
        order = module.BookingOrder.from_payload(payload)
        for quote in module.PolicyRegistry.quote_all(order, item["policy_codes"]):
            prefix = f"{label}.{quote.policy_code}"
            expected[f"{prefix}.line"] = quote.render_line()
            expected[f"{prefix}.fees"] = str(quote.grand_fees)
            expected[f"{prefix}.discount"] = str(quote.discount_amount)

    ledger_cfg = scenarios["ledger"]
    ledger = module.PricingLedger.from_payloads(ledger_cfg["payloads"], ledger_cfg["policy_codes"])
    expected["ledger.quote_count"] = str(len(ledger.quotes))
    expected["ledger.total_due"] = str(ledger.total_due())
    expected["ledger.total_discount"] = str(ledger.total_discount())
    expected["ledger.report"] = ledger.render_report()
    return expected


def build_runner(scenarios: dict[str, object]) -> str:
    matrix_lines: list[str] = []
    for item in scenarios["matrix"]:
        matrix_lines.append(
            f'      ({to_scala(item["label"])}, {to_scala(item["policy_codes"])}, {to_scala(item["payload"])}),'
        )
    payload_lines = [f"      {to_scala(payload)}," for payload in scenarios["ledger"]["payloads"]]

    return f"""import booking._

object TestRunner {{
  private def line(key: String, value: String): Unit = println(s"$key=$value")

  def main(args: Array[String]): Unit = {{
    line("supported_codes", PolicyRegistry.supportedCodes.mkString(","))

    val matrix = Vector(
{chr(10).join(matrix_lines)}
    )

    matrix.foreach {{ case (label, policyCodes, payload) =>
      val order = BookingOrder.fromPayload(payload)
      val quotes = PolicyRegistry.quoteAll(order, policyCodes)
      quotes.foreach {{ quote =>
        val prefix = s"${{label}}.${{quote.policyCode}}"
        line(s"${{prefix}}.line", quote.renderLine)
        line(s"${{prefix}}.fees", quote.grandFees.toString)
        line(s"${{prefix}}.discount", quote.discountAmount.toString)
      }}
    }}

    val ledger = PricingLedger.fromPayloads(
      Vector(
{chr(10).join(payload_lines)}
      ),
      {to_scala(scenarios["ledger"]["policy_codes"])}
    )

    line("ledger.quote_count", ledger.quotes.size.toString)
    line("ledger.total_due", ledger.totalDue.toString)
    line("ledger.total_discount", ledger.totalDiscount.toString)
    line("ledger.report", ledger.renderReport)
  }}
}}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scala_file")
    parser.add_argument("source_file")
    parser.add_argument("scenario_file")
    args = parser.parse_args()

    scala_file = Path(args.scala_file)
    source_file = Path(args.source_file)
    scenario_file = Path(args.scenario_file)

    if not source_file.exists():
        raise SystemExit(f"缺少输入资产: {source_file}")
    if not scenario_file.exists():
        raise SystemExit(f"缺少场景资产: {scenario_file}")
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
    scenarios = json.loads(scenario_file.read_text(encoding="utf-8"))
    expected = build_expected(module, scenarios)
    runner_source = build_runner(scenarios)

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
