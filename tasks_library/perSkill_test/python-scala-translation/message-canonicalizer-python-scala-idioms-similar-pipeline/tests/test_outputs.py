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
    ("MessageLike", r"trait\s+MessageLike\b"),
    ("MessageProcessor", r"trait\s+MessageProcessor\b"),
    ("MessageKind", r"sealed\s+trait\s+MessageKind\b"),
    ("CanonicalMessage", r"case\s+class\s+CanonicalMessage\b"),
    ("BaseCanonicalizer", r"abstract\s+class\s+BaseCanonicalizer\b"),
    ("TextCanonicalizer", r"class\s+TextCanonicalizer\b"),
    ("MetricCanonicalizer", r"class\s+MetricCanonicalizer\b"),
    ("StructuredCanonicalizer", r"class\s+StructuredCanonicalizer\b"),
    ("MessagePipeline", r"class\s+MessagePipeline\b"),
    ("MessageCanonicalizer object", r"object\s+MessageCanonicalizer\b"),
    ("Option", r"Option\["),
    ("Pattern matching", r"\bmatch\s*\{"),
    ("Collection transform", r"\.foldLeft\b|\.map\b|\.collect\b"),
]

FORBIDDEN_PATTERNS = [
    (r"\basInstanceOf\[", "不要使用 asInstanceOf"),
    (r"\breturn\b", "不要依赖显式 return"),
    (r"throw\s+new\s+Exception", "不要抛出过于泛化的 Exception"),
]

HARNESS = """import java.time.LocalDateTime

object ScalaHarness {
  final case class Alert(raw: String) extends MessageLike {
    override def canonicalText: String = raw
  }

  object AuditTagger extends MessageProcessor {
    override def process(message: CanonicalMessage): CanonicalMessage =
      message.kind match {
        case MessageKind.Text => message.withTags("audited")
        case _ => message
      }
  }

  def assertEquals[A](label: String, actual: A, expected: A): Unit =
    if (actual != expected) {
      throw new AssertionError(s"$label expected: $expected but was: $actual")
    }

  def main(args: Array[String]): Unit = {
    val textCanonicalizer = new TextCanonicalizer(lowercase = true)
    val text = textCanonicalizer.canonicalize("  Hello   WORLD  ")
    assertEquals("text.body", text.body, "hello world")
    assertEquals("text.kind", text.kind, MessageKind.Text)
    assertEquals("text.channel", text.channel, None)

    val duck = textCanonicalizer.canonicalize(Alert("  Ping   OK "))
    assertEquals("duck.body", duck.body, "ping ok")

    val bytes = textCanonicalizer.canonicalize("  Byte  Data ".getBytes("UTF-8"))
    assertEquals("bytes.body", bytes.body, "byte data")

    val metric = new MetricCanonicalizer(precision = 3).canonicalize(BigDecimal("12.3009"))
    assertEquals("metric.body", metric.body, "12.301")
    assertEquals("metric.kind", metric.kind, MessageKind.Metric)
    assertEquals("metric.channel", metric.channel, Some("metrics"))
    assertEquals("metric.sourceType", metric.attributes.get("source_type"), Some("BigDecimal"))

    val structured = new StructuredCanonicalizer(precision = 2).canonicalize(
      Map(
        "channel" -> " Alerts ",
        "tags" -> Seq("Pager", " pager ", "Ops"),
        "observed_at" -> LocalDateTime.of(2026, 1, 3, 4, 5, 6),
        "message" -> "  Deploy   started ",
        "ok" -> true,
        "count" -> 2,
        "details" -> Map("region" -> " us-east ", "durations" -> Seq(1, 2, 3), "skip" -> None)
      )
    )
    assertEquals("structured.kind", structured.kind, MessageKind.Event)
    assertEquals(
      "structured.body",
      structured.body,
      "{count:2,details:{durations:[1,2,3],region:us-east},message:Deploy started,ok:true}"
    )
    assertEquals("structured.channel", structured.channel, Some("alerts"))
    assertEquals("structured.tags", structured.tags, Vector("ops", "pager"))
    assertEquals("structured.observedAt", structured.observedAt, Some("2026-01-03T04:05:06"))
    assertEquals("structured.fieldCount", structured.attributes.get("field_count"), Some("4"))

    val empty = MessageCanonicalizer.canonicalizeMessage(None)
    assertEquals("empty.kind", empty.kind, MessageKind.Empty)
    assertEquals("empty.body", empty.body, "")

    val pipeline = new MessagePipeline(processors = Seq(AuditTagger))
    val batch = pipeline.run(
      Seq(
        "  Hi There ",
        BigDecimal("7.125"),
        Map("message" -> "  Ready ", "tags" -> Seq("Release"))
      )
    )
    assertEquals("batch.size", batch.size, 3)
    assertEquals("batch.first.tags", batch.head.tags, Vector("audited"))
    assertEquals("batch.second.body", batch(1).body, "7.13")
    assertEquals("batch.third.kind", batch(2).kind, MessageKind.Event)

    val direct = MessageCanonicalizer.canonicalizeBatch(
      Seq(
        Alert("  Keep  Calm "),
        5,
        Map("message" -> " Ship It ", "channel" -> "Ops")
      )
    )
    assertEquals("direct.size", direct.size, 3)
    assertEquals("direct.first.body", direct.head.body, "keep calm")
    assertEquals("direct.second.sourceType", direct(1).attributes.get("source_type"), Some("Int"))
    assertEquals("direct.third.channel", direct(2).channel, Some("ops"))

    val summary = MessageCanonicalizer.summarizeByKind(batch ++ direct :+ structured)
    assertEquals("summary", summary, Map("text" -> 2, "metric" -> 2, "event" -> 3))

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

        user_target = tmpdir / "MessageCanonicalizer.scala"
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
