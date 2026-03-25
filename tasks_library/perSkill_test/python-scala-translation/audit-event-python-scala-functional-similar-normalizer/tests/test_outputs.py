#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


SCALA_FILE = Path("/root/EventNormalizer.scala")

HARNESS = """
object EventNormalizerHarness {
  private def emit(key: String, value: String): Unit =
    println(s"$key=$value")

  def main(args: Array[String]): Unit = {
    val closure = EventNormalizer.makeFieldNormalizer(
      aliases = Map("svc-root" -> "root-admin"),
      defaultValue = Some("fallback"),
      transform = _.replace(" ", "_")
    )
    emit("closure.alias", closure(Some(" svc-root ")).getOrElse("NONE"))
    emit("closure.blank", closure(Some("   ")).getOrElse("NONE"))
    emit("closure.none", closure(None).getOrElse("NONE"))

    val merged = EventNormalizer.mergeMetadata(
      Some(Map("source" -> "audit", "trace" -> "base")),
      Some(Map("trace" -> "event", "team" -> "risk"))
    )
    emit("metadata.merged", merged.toSeq.sortBy(_._1).map { case (k, v) => s"$k:$v" }.mkString(","))

    val auditEvent = AuditEvent(
      actor = Some(" svc-root "),
      action = " Read Report ",
      resource = None,
      tags = Seq("Finance", " ", "PII", "finance"),
      metadata = Some(Map("trace" -> "event-7", "team" -> "risk"))
    ).withMetadata("ticket" -> "SEC-9")

    emit("audit.withMetadata", auditEvent.metadata.flatMap(_.get("ticket")).getOrElse("NONE"))

    val normalizer = new AuditEventNormalizer(
      actorAliases = Map("svc-root" -> "root-admin"),
      resourceAliases = Map("control-plane" -> "control-plane"),
      baseMetadata = Map("source" -> "audit", "trace" -> "base")
    )

    emit("kind.login", normalizer.inferKind(" Login ").value)
    emit("kind.read", normalizer.inferKind(" Read Report ").value)
    emit("kind.config", normalizer.inferKind(" rotate secrets ").value)
    emit("kind.other", normalizer.inferKind(" escalate ").value)

    val normalized = normalizer.normalize(auditEvent)
    emit("normalized.actor", normalized.actor)
    emit("normalized.action", normalized.action)
    emit("normalized.resource", normalized.resource)
    emit("normalized.kind", normalized.kind.value)
    emit("normalized.tags", normalized.tags.mkString(","))
    emit("normalized.meta.trace", normalized.metadata.getOrElse("trace", "NONE"))
    emit("normalized.meta.source", normalized.metadata.getOrElse("source", "NONE"))
    emit("normalized.meta.ticket", normalized.metadata.getOrElse("ticket", "NONE"))
    emit("normalized.withMetadata", normalized.withMetadata("reviewed" -> "yes").metadata.getOrElse("reviewed", "NONE"))

    var pulls = 0
    val upstream = new Iterator[AuditEvent] {
      private val items = Vector(
        AuditEvent(None, "Login", Some(" console "), Seq("Auth"), None),
        AuditEvent(Some("alice"), "config policy", Some(" control-plane "), Seq("Ops"), Some(Map("ticket" -> "CHG-77")))
      )
      private var index = 0

      override def hasNext: Boolean = index < items.length

      override def next(): AuditEvent = {
        val item = items(index)
        index += 1
        pulls += 1
        item
      }
    }

    val lazyBatch = normalizer.normalizeBatch(upstream)
    emit("batch.pulls.before", pulls.toString)
    val first = lazyBatch.next()
    emit("batch.pulls.after.one", pulls.toString)
    emit("batch.first.actor", first.actor)
    emit("batch.first.resource", first.resource)
    val second = lazyBatch.next()
    emit("batch.pulls.after.two", pulls.toString)
    emit("batch.second.kind", second.kind.value)
    emit("batch.second.ticket", second.metadata.getOrElse("ticket", "NONE"))

    val streamed = EventNormalizer.normalizeEvents(
      List(
        AuditEvent(None, "Login", None, Seq("Auth"), None),
        AuditEvent(Some("Bob"), " export data ", Some(" warehouse "), Seq("Finance"), Some(Map("trace" -> "export-1")))
      ),
      Some(normalizer.withMetadata("pipeline" -> "nightly"))
    ).toVector

    emit("streamed.size", streamed.size.toString)
    emit("streamed.second.kind", streamed(1).kind.value)
    emit("streamed.second.pipeline", streamed(1).metadata.getOrElse("pipeline", "NONE"))
    emit("streamed.second.actor", streamed(1).actor)
  }
}
"""


def ensure_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise AssertionError(f"missing required tool: {name}")


def parse_output(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def run_harness() -> dict[str, str]:
    if not SCALA_FILE.exists():
        raise AssertionError("/root/EventNormalizer.scala not found")

    ensure_tool("scalac")
    ensure_tool("scala")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        classes = tmp / "classes"
        classes.mkdir()
        harness_path = tmp / "EventNormalizerHarness.scala"
        harness_path.write_text(HARNESS, encoding="utf-8")

        compile_cmd = [
            "scalac",
            "-d",
            str(classes),
            str(SCALA_FILE),
            str(harness_path),
        ]
        compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True, check=False)
        if compile_proc.returncode != 0:
            raise AssertionError(f"scalac failed:\\n{compile_proc.stdout}\\n{compile_proc.stderr}")

        run_cmd = [
            "scala",
            "-cp",
            str(classes),
            "EventNormalizerHarness",
        ]
        run_proc = subprocess.run(run_cmd, capture_output=True, text=True, check=False)
        if run_proc.returncode != 0:
            raise AssertionError(f"scala run failed:\\n{run_proc.stdout}\\n{run_proc.stderr}")

        return parse_output(run_proc.stdout)


def expect(results: dict[str, str], key: str, expected: str) -> None:
    actual = results.get(key)
    if actual != expected:
        raise AssertionError(f"{key} expected {expected!r}, got {actual!r}")


def main() -> None:
    results = run_harness()

    expect(results, "closure.alias", "root-admin")
    expect(results, "closure.blank", "fallback")
    expect(results, "closure.none", "fallback")
    expect(results, "metadata.merged", "source:audit,team:risk,trace:event")
    expect(results, "audit.withMetadata", "SEC-9")

    expect(results, "kind.login", "login")
    expect(results, "kind.read", "data_access")
    expect(results, "kind.config", "config_change")
    expect(results, "kind.other", "other")

    expect(results, "normalized.actor", "root-admin")
    expect(results, "normalized.action", "read_report")
    expect(results, "normalized.resource", "unknown-resource")
    expect(results, "normalized.kind", "data_access")
    expect(results, "normalized.tags", "finance,pii")
    expect(results, "normalized.meta.trace", "event-7")
    expect(results, "normalized.meta.source", "audit")
    expect(results, "normalized.meta.ticket", "SEC-9")
    expect(results, "normalized.withMetadata", "yes")

    expect(results, "batch.pulls.before", "0")
    expect(results, "batch.pulls.after.one", "1")
    expect(results, "batch.first.actor", "system")
    expect(results, "batch.first.resource", "console")
    expect(results, "batch.pulls.after.two", "2")
    expect(results, "batch.second.kind", "config_change")
    expect(results, "batch.second.ticket", "CHG-77")

    expect(results, "streamed.size", "2")
    expect(results, "streamed.second.kind", "data_access")
    expect(results, "streamed.second.pipeline", "nightly")
    expect(results, "streamed.second.actor", "bob")


if __name__ == "__main__":
    main()
