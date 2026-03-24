#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REQUIRED_PATTERNS = [
    ("Severity", r"sealed\s+trait\s+Severity\b"),
    ("DeliveryChannel", r"sealed\s+trait\s+DeliveryChannel\b"),
    ("ScheduleWindow", r"case\s+class\s+ScheduleWindow\b"),
    ("EscalationPolicy", r"case\s+class\s+EscalationPolicy\b"),
    ("Alert", r"case\s+class\s+Alert\b"),
    ("EscalationStep", r"case\s+class\s+EscalationStep\b"),
    ("RoutingDecision", r"case\s+class\s+RoutingDecision\b"),
    ("ServicePolicy", r"case\s+class\s+ServicePolicy\b"),
    ("AlertRouter", r"class\s+AlertRouter\b"),
    ("AlertRouting object", r"object\s+AlertRouting\b"),
    ("Option", r"Option\["),
    ("Pattern matching", r"\bmatch\s*\{"),
    ("Collection pipeline", r"\.foldLeft\b|\.map\b|\.collect\b|\.flatMap\b"),
]

FORBIDDEN_PATTERNS = [
    (r"\basInstanceOf\[", "不要使用 asInstanceOf"),
    (r"\breturn\b", "不要依赖显式 return"),
    (r"throw\s+new\s+Exception", "不要抛出过于泛化的 Exception"),
]

HARNESS = r"""object ScalaHarness {
  def assertEquals[A](label: String, actual: A, expected: A): Unit =
    if (actual != expected) {
      throw new AssertionError(s"$label expected: $expected but was: $actual")
    }

  def main(args: Array[String]): Unit = {
    val router = AlertRouting.defaultRouter

    val businessWindow = router.activeWindow("payments", 10).map(_.name)
    assertEquals("businessWindow", businessWindow, Some("business"))

    val vipWarning = Alert(
      service = "payments",
      severity = Severity.Warning,
      createdHour = 10,
      tags = Vector(" VIP ", "checkout")
    )
    val vipDecision = AlertRouting.routeAlert(vipWarning)
    assertEquals("vip.service", vipDecision.service, "payments")
    assertEquals("vip.activeWindow", vipDecision.activeWindow, Some("business"))
    assertEquals("vip.fallbackUsed", vipDecision.fallbackUsed, false)
    assertEquals("vip.dedupKey", vipDecision.dedupKey, "payments:warning:checkout,vip")
    assertEquals(
      "vip.steps",
      vipDecision.steps.map(step => (step.channel.label, step.targets, step.delayMinutes, step.note)),
      Vector(
        ("pager", Vector("maya", "nico"), 0, "tag override"),
        ("email", Vector("payments-manager"), 20, "escalation")
      )
    )

    val overnightInfo = Alert(
      service = "platform",
      severity = Severity.Info,
      createdHour = 2,
      tags = Vector("maintenance")
    )
    val overnightInfoDecision = AlertRouting.routeAlert(overnightInfo)
    assertEquals("overnightInfo.window", overnightInfoDecision.activeWindow, Some("overnight"))
    assertEquals("overnightInfo.fallback", overnightInfoDecision.fallbackUsed, true)
    assertEquals(
      "overnightInfo.steps",
      overnightInfoDecision.steps.map(step => (step.channel.label, step.targets, step.delayMinutes, step.note)),
      Vector(("email", Vector("global-noc"), 0, "after-hours digest"))
    )

    val critical = Alert(
      service = "payments",
      severity = Severity.Critical,
      createdHour = 23,
      tags = Vector("db")
    )
    val criticalDecision = AlertRouting.routeAlert(critical)
    assertEquals("critical.window", criticalDecision.activeWindow, Some("overnight"))
    assertEquals("critical.fallback", criticalDecision.fallbackUsed, false)
    assertEquals(
      "critical.steps",
      criticalDecision.steps.map(step => (step.channel.label, step.targets, step.delayMinutes)),
      Vector(
        ("pager", Vector("night-pay", "incident-commander"), 0),
        ("phone", Vector("incident-commander"), 5)
      )
    )
    assertEquals(
      "critical.targets",
      AlertRouting.escalationTargets(criticalDecision),
      Vector("night-pay", "incident-commander")
    )

    val unknown = Alert(
      service = "search",
      severity = Severity.Warning,
      createdHour = 12,
      tags = Vector("search")
    )
    val unknownDecision = AlertRouting.routeAlert(unknown)
    assertEquals("unknown.service", unknownDecision.service, "default")
    assertEquals("unknown.window", unknownDecision.activeWindow, None)
    assertEquals("unknown.fallback", unknownDecision.fallbackUsed, true)
    assertEquals(
      "unknown.steps",
      unknownDecision.steps.map(step => (step.channel.label, step.targets, step.delayMinutes)),
      Vector(
        ("phone", Vector("global-noc"), 0),
        ("email", Vector("global-noc"), 20)
      )
    )

    val businessInfo = Alert(
      service = "platform",
      severity = Severity.Info,
      createdHour = 11,
      tags = Vector("release")
    )

    val routed = AlertRouting.routeBatch(Vector(businessInfo, vipWarning, overnightInfo, critical, unknown))
    assertEquals("routeBatch.size", routed.size, 5)
    assertEquals(
      "summary",
      AlertRouting.summarizeByChannel(routed),
      Map("chat" -> 1, "email" -> 3, "pager" -> 2, "phone" -> 2)
    )

    println("ok")
  }
}
"""


def fail(message: str) -> int:
    print(message)
    return 1


def check_source(source: str) -> list[str]:
    errors: list[str] = []

    for label, pattern in REQUIRED_PATTERNS:
        if not re.search(pattern, source):
            errors.append(f"缺少必要结构: {label}")

    for pattern, message in FORBIDDEN_PATTERNS:
        if re.search(pattern, source):
            errors.append(message)

    if re.search(r"\bnull\b", source):
        errors.append("提交中出现了 null，应该优先使用 Option 表达缺失值。")

    return errors


def compile_and_run(scala_file: Path) -> tuple[int, str]:
    scalac = shutil.which("scalac")
    scala = shutil.which("scala")
    if not scalac or not scala:
        return 1, "找不到 scalac 或 scala，请检查环境。"

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        classes_dir = tmpdir / "classes"
        classes_dir.mkdir(parents=True, exist_ok=True)

        user_target = tmpdir / "AlertRouting.scala"
        user_target.write_text(scala_file.read_text(encoding="utf-8"), encoding="utf-8")

        harness_target = tmpdir / "ScalaHarness.scala"
        harness_target.write_text(HARNESS, encoding="utf-8")

        compile_proc = subprocess.run(
            [scalac, "-d", str(classes_dir), str(user_target), str(harness_target)],
            capture_output=True,
            text=True,
        )
        if compile_proc.returncode != 0:
            return compile_proc.returncode, compile_proc.stdout + compile_proc.stderr

        run_proc = subprocess.run(
            [scala, "-cp", str(classes_dir), "ScalaHarness"],
            capture_output=True,
            text=True,
        )
        return run_proc.returncode, run_proc.stdout + run_proc.stderr


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scala_file")
    args = parser.parse_args()

    scala_file = Path(args.scala_file)
    if not scala_file.exists():
        return fail(f"未找到输出文件: {scala_file}")

    source = scala_file.read_text(encoding="utf-8")
    errors = check_source(source)
    if errors:
        return fail("\n".join(errors))

    code, output = compile_and_run(scala_file)
    if code != 0:
        return fail(output.strip() or "Scala 编译或运行失败。")

    print(output.strip() or "ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
