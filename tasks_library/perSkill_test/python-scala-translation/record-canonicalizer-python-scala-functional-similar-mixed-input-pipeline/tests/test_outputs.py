#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCALA_FILE = Path("/root/RecordCanonicalizer.scala")

REQUIRED_PATTERNS = {
    "FieldKind": r"(sealed\s+trait|enum)\s+FieldKind",
    "CanonicalField": r"case\s+class\s+CanonicalField",
    "CanonicalValue": r"trait\s+CanonicalValue",
    "BaseCanonicalizer": r"(abstract\s+class|trait)\s+BaseCanonicalizer",
    "TextCanonicalizer": r"class\s+TextCanonicalizer",
    "NumericCanonicalizer": r"class\s+NumericCanonicalizer",
    "TemporalCanonicalizer": r"class\s+TemporalCanonicalizer",
    "RecordCanonicalizer": r"class\s+RecordCanonicalizer",
    "CanonicalizerBuilder": r"(case\s+class|class)\s+CanonicalizerBuilder",
    "withMetadata": r"def\s+withMetadata\s*\(",
    "canonicalizeBatch": r"def\s+canonicalizeBatch\s*\(",
    "composeNormalizers": r"def\s+composeNormalizers\s*\(",
    "streamTextSegments": r"def\s+streamTextSegments\s*\(",
}

STYLE_PATTERNS = {
    "option": r"Option\[",
    "match": r"\bmatch\s*\{",
    "iterator": r"Iterator\[",
    "case_object": r"case\s+object",
}

VERIFIER_SOURCE = r"""
import java.time.{LocalDate, LocalDateTime}
import scala.collection.immutable.ListMap

object RecordCanonicalizerVerifier extends App {
  def ensure(condition: Boolean, message: String): Unit =
    if (!condition) throw new AssertionError(message)

  val normalizer = RecordCanonicalizer.composeNormalizers(
    _.trim,
    _.toLowerCase,
    _.replace(" ", "_")
  )
  ensure(normalizer("  Display Name  ") == "display_name", "composeNormalizers should compose in order")

  val textCanonicalizer = new TextCanonicalizer(
    keyNormalizer = _.trim.toLowerCase.replace(" ", "_"),
    valueNormalizer = RecordCanonicalizer.composeNormalizers(_.trim, _.replace(" ", "-"))
  )
  val textField = textCanonicalizer.canonicalize(" Display Name ", "  Alice Smith  ", Map("source" -> "form"))
  ensure(textField.key == "display_name", "text key should be normalized")
  ensure(textField.value == "Alice-Smith", "text value should be normalized")
  ensure(textField.kind == FieldKind.Text, "text kind mismatch")
  ensure(textField.metadata("source") == "form", "text metadata mismatch")

  val numericField = new NumericCanonicalizer(precision = 3).canonicalize("amount", BigDecimal("12.3456"))
  ensure(numericField.value == "12.346", "numeric precision mismatch")
  ensure(numericField.metadata("original_type").toString.nonEmpty, "numeric metadata missing original type")

  val temporalField = new TemporalCanonicalizer().canonicalize("created_at", LocalDateTime.of(2025, 1, 2, 3, 4, 5))
  ensure(temporalField.value == "2025-01-02T03:04:05", "temporal formatting mismatch")

  val recordCanonicalizer = CanonicalizerBuilder()
    .withKeyNormalizer(_.trim.toLowerCase.replace(" ", "_"))
    .withTextNormalizer(_.trim)
    .withTextNormalizer(_.replace(" ", "-"))
    .withMetadata("source" -> "ingest")
    .withPrecision(4)
    .build()

  val customField = recordCanonicalizer.canonicalize(
    " profile ",
    new CanonicalValue {
      override def canonicalValue: String = "external-42"
    }
  )
  ensure(customField.kind == FieldKind.Structured, "custom canonical value should dispatch to structured")
  ensure(customField.value == "external-42", "custom canonical value mismatch")
  ensure(customField.metadata("source") == "ingest", "builder metadata should flow into fields")

  val record = ListMap[String, Any](
    " Display Name " -> "  Ada Lovelace  ",
    "amount" -> BigDecimal("3.14159"),
    "active" -> true,
    "created" -> LocalDate.of(2024, 4, 5),
    "notes" -> Vector("first", "second"),
    "missing" -> None
  )

  val canonicalRecord = recordCanonicalizer.canonicalizeRecord(
    record,
    Some((key: String, value: Any) => Map("seen_key" -> key.trim, "is_empty" -> (value == None)))
  )

  ensure(canonicalRecord.map(_.key) == Vector("display_name", "amount", "active", "created", "notes", "missing"), "record key order mismatch")
  ensure(canonicalRecord.head.value == "Ada-Lovelace", "record text normalization mismatch")
  ensure(canonicalRecord(1).value == "3.1416", "record numeric precision mismatch")
  ensure(canonicalRecord(2).kind == FieldKind.Flag, "boolean dispatch mismatch")
  ensure(canonicalRecord(3).kind == FieldKind.Temporal, "date dispatch mismatch")
  ensure(canonicalRecord(4).metadata("structured") == true, "structured metadata missing")
  ensure(canonicalRecord.last.kind == FieldKind.Empty, "None should map to empty")
  ensure(canonicalRecord.last.metadata("is_empty") == true, "metadata factory output mismatch")

  var pulled = 0
  val records = Iterator(
    ListMap[String, Any]("name" -> " First Row ", "score" -> 7),
    ListMap[String, Any]("name" -> " Second Row ", "score" -> 8),
    ListMap[String, Any]("name" -> " Third Row ", "score" -> 9)
  ).map { record =>
    pulled += 1
    record
  }

  val batched = recordCanonicalizer.canonicalizeRecords(records, batchSize = 2)
  ensure(pulled == 0, "batching should be lazy before consumption")
  val firstBatch = batched.next()
  ensure(pulled == 2, "first batch should only consume two records")
  ensure(firstBatch.map(_.key) == Vector("name", "score", "name", "score"), "first batch contents mismatch")
  val secondBatch = batched.next()
  ensure(secondBatch.size == 2, "second batch should contain one record worth of fields")

  val segmented = RecordCanonicalizer.streamTextSegments("  alpha beta\n gamma  ").toVector
  ensure(segmented == Vector(0 -> "alpha", 1 -> "beta", 2 -> "gamma"), "streamTextSegments mismatch")

  val merged = canonicalRecord.head.withMetadata("checked" -> true)
  ensure(merged.metadata("checked") == true, "withMetadata should merge metadata")
  ensure(!canonicalRecord.head.metadata.contains("checked"), "withMetadata should return a new field")
}
"""


def fail(message: str) -> None:
    print(message)
    sys.exit(1)


def ensure_file() -> str:
    if not SCALA_FILE.is_file():
        fail(f"missing output file: {SCALA_FILE}")
    return SCALA_FILE.read_text(encoding="utf-8")


def check_source(source: str) -> None:
    missing = [name for name, pattern in REQUIRED_PATTERNS.items() if not re.search(pattern, source)]
    if missing:
        fail("missing required Scala components: " + ", ".join(missing))

    missing_style = [name for name, pattern in STYLE_PATTERNS.items() if not re.search(pattern, source)]
    if missing_style:
        fail("Scala implementation is missing expected functional patterns: " + ", ".join(missing_style))


def compile_and_run(source_path: Path) -> None:
    scalac = shutil.which("scalac")
    scala = shutil.which("scala")
    if not scalac or not scala:
        fail("scala toolchain not found in PATH")

    with tempfile.TemporaryDirectory(prefix="record-canonicalizer-verify-") as tmpdir:
        tmp = Path(tmpdir)
        candidate = tmp / "RecordCanonicalizer.scala"
        verifier = tmp / "Verifier.scala"
        classes = tmp / "classes"
        classes.mkdir()

        candidate.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        verifier.write_text(VERIFIER_SOURCE, encoding="utf-8")

        compile_proc = subprocess.run(
            [scalac, "-deprecation", "-feature", "-d", str(classes), str(candidate), str(verifier)],
            text=True,
            capture_output=True,
        )
        if compile_proc.returncode != 0:
            fail("scalac failed:\n" + compile_proc.stdout + compile_proc.stderr)

        run_proc = subprocess.run(
            [scala, "-cp", str(classes), "RecordCanonicalizerVerifier"],
            text=True,
            capture_output=True,
        )
        if run_proc.returncode != 0:
            fail("behavior verification failed:\n" + run_proc.stdout + run_proc.stderr)


def main() -> None:
    source = ensure_file()
    check_source(source)
    compile_and_run(SCALA_FILE)
    print("ok")


if __name__ == "__main__":
    main()
