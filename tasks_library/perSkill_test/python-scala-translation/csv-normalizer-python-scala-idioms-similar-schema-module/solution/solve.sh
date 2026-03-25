#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/CsvNormalizer.scala
package csvnormalizer

import scala.math.BigDecimal.RoundingMode
import scala.util.Try

sealed trait ColumnKind
object ColumnKind {
  case object Text extends ColumnKind
  case object Integer extends ColumnKind
  case object Decimal extends ColumnKind
  case object Flag extends ColumnKind
  case object Tags extends ColumnKind
}

sealed trait NormalizedValue
final case class TextValue(value: String) extends NormalizedValue
final case class IntegerValue(value: Int) extends NormalizedValue
final case class DecimalValue(value: BigDecimal) extends NormalizedValue
final case class FlagValue(value: Boolean) extends NormalizedValue
final case class TagsValue(value: Vector[String]) extends NormalizedValue

final case class ColumnSpec(
  outputName: String,
  sourceName: String,
  kind: ColumnKind,
  required: Boolean = true,
  aliases: Vector[String] = Vector.empty,
  defaultRaw: Option[String] = None,
  parser: Option[String => NormalizedValue] = None
) {
  def candidates: Vector[String] = sourceName +: aliases
}

final case class NormalizationIssue(
  column: String,
  message: String,
  rawValue: Option[String] = None
)

final case class NormalizedRow(
  values: Map[String, Option[NormalizedValue]],
  issues: Vector[NormalizationIssue] = Vector.empty,
  metadata: Map[String, String] = Map.empty
) {
  def withMetadata(entries: (String, String)*): NormalizedRow =
    copy(metadata = metadata ++ entries.toMap)
}

final class CsvNormalizer(val schema: Seq[ColumnSpec], val sourceLabel: String) {
  def headers(): Vector[String] =
    schema.toVector.map(_.outputName)

  def normalizeRow(rawRow: Map[String, String], rowNumber: Int): NormalizedRow = {
    val result = schema.toVector.foldLeft(RowAccum.empty) { (acc, spec) =>
      val (matchedKey, rawValue) = pickValue(spec, rawRow)
      val nextMatched = matchedKey.fold(acc.matchedInputs)(acc.matchedInputs :+ _)
      val resolvedValue = rawValue.map(_.trim).filter(_.nonEmpty).orElse(spec.defaultRaw.map(_.trim).filter(_.nonEmpty))

      resolvedValue match {
        case None if spec.required =>
          acc.copy(
            values = acc.values + (spec.outputName -> None),
            issues = acc.issues :+ NormalizationIssue(spec.outputName, "missing required value", rawValue),
            matchedInputs = nextMatched
          )
        case None =>
          acc.copy(
            values = acc.values + (spec.outputName -> None),
            matchedInputs = nextMatched
          )
        case Some(text) =>
          val parser = spec.parser.getOrElse(CsvNormalizer.defaultParser(spec.kind))
          Try(parser(text)).toEither match {
            case Right(value) =>
              acc.copy(
                values = acc.values + (spec.outputName -> Some(value)),
                matchedInputs = nextMatched
              )
            case Left(error) =>
              acc.copy(
                values = acc.values + (spec.outputName -> None),
                issues = acc.issues :+ NormalizationIssue(spec.outputName, error.getMessage, Some(text)),
                matchedInputs = nextMatched
              )
          }
      }
    }

    NormalizedRow(result.values, result.issues).withMetadata(
      "source" -> sourceLabel,
      "rowNumber" -> rowNumber.toString,
      "matchedInputs" -> result.matchedInputs.mkString(","),
      "issueCount" -> result.issues.length.toString
    )
  }

  def normalizeRows(rows: Iterable[Map[String, String]], startRow: Int = 1): Iterator[NormalizedRow] =
    rows.iterator.zipWithIndex.map { case (row, offset) =>
      normalizeRow(row, startRow + offset)
    }

  private def pickValue(spec: ColumnSpec, rawRow: Map[String, String]): (Option[String], Option[String]) =
    spec.candidates.find(rawRow.contains) match {
      case Some(key) => Some(key) -> rawRow.get(key)
      case None => None -> None
    }
}

object CsvNormalizer {
  def parseInteger(raw: String): NormalizedValue =
    IntegerValue(raw.trim.toInt)

  def parseDecimal(raw: String): NormalizedValue =
    DecimalValue(BigDecimal(raw.trim).setScale(2, RoundingMode.HALF_UP))

  def parseFlag(raw: String): NormalizedValue = {
    raw.trim.toLowerCase match {
      case "true" | "1" | "yes" | "y" => FlagValue(true)
      case "false" | "0" | "no" | "n" => FlagValue(false)
      case other => throw new IllegalArgumentException(s"unsupported flag value: '$other'")
    }
  }

  def parseTags(raw: String): NormalizedValue =
    TagsValue(raw.split("\\|").iterator.map(_.trim.toLowerCase).filter(_.nonEmpty).toVector)

  def catalogSchema(): Vector[ColumnSpec] =
    Vector(
      ColumnSpec("sku", "sku", ColumnKind.Text),
      ColumnSpec("warehouse", "warehouse", ColumnKind.Text, aliases = Vector("site")),
      ColumnSpec("quantity", "qty", ColumnKind.Integer),
      ColumnSpec("unitPrice", "unit_price", ColumnKind.Decimal, required = false),
      ColumnSpec("active", "active", ColumnKind.Flag, required = false, defaultRaw = Some("yes")),
      ColumnSpec("tags", "labels", ColumnKind.Tags, required = false)
    )

  private[csvnormalizer] def defaultParser(kind: ColumnKind): String => NormalizedValue = kind match {
    case ColumnKind.Text => raw => TextValue(raw.trim)
    case ColumnKind.Integer => parseInteger _
    case ColumnKind.Decimal => parseDecimal _
    case ColumnKind.Flag => parseFlag _
    case ColumnKind.Tags => parseTags _
  }
}

private final case class RowAccum(
  values: Map[String, Option[NormalizedValue]],
  issues: Vector[NormalizationIssue],
  matchedInputs: Vector[String]
)

private object RowAccum {
  val empty: RowAccum = RowAccum(Map.empty, Vector.empty, Vector.empty)
}
EOF
