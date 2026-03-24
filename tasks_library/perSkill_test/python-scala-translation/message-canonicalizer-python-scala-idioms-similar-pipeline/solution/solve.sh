#!/bin/bash
set -euo pipefail

output_path="${OUTPUT_PATH:-/root/MessageCanonicalizer.scala}"

cat <<'EOF' > "$output_path"
import java.nio.charset.StandardCharsets
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

import scala.math.BigDecimal.RoundingMode

trait MessageLike {
  def canonicalText: String
}

trait MessageProcessor {
  def process(message: CanonicalMessage): CanonicalMessage
}

sealed trait MessageKind {
  def value: String
}

object MessageKind {
  case object Text extends MessageKind {
    val value: String = "text"
  }

  case object Event extends MessageKind {
    val value: String = "event"
  }

  case object Metric extends MessageKind {
    val value: String = "metric"
  }

  case object Empty extends MessageKind {
    val value: String = "empty"
  }
}

final case class CanonicalMessage(
  body: String,
  kind: MessageKind,
  channel: Option[String] = None,
  tags: Vector[String] = Vector.empty,
  attributes: Map[String, String] = Map.empty,
  observedAt: Option[String] = None
) {
  def withAttributes(entries: (String, String)*): CanonicalMessage =
    copy(attributes = attributes ++ entries.toMap)

  def withTags(extra: String*): CanonicalMessage = {
    val merged = (tags ++ extra.map(MessageCanonicalizer.normalizeToken))
      .filter(_.nonEmpty)
      .distinct
      .sorted
      .toVector

    copy(tags = merged)
  }
}

abstract class BaseCanonicalizer[-A] {
  def canonicalize(value: A): CanonicalMessage

  def canonicalizeBatch(values: Iterable[A]): Vector[CanonicalMessage] =
    values.iterator.map(canonicalize).toVector
}

final class TextCanonicalizer(lowercase: Boolean = true) extends BaseCanonicalizer[String] {
  override def canonicalize(value: String): CanonicalMessage =
    canonicalizeRaw(value)

  def canonicalize(value: Array[Byte]): CanonicalMessage =
    canonicalizeRaw(new String(value, StandardCharsets.UTF_8))

  def canonicalize(value: MessageLike): CanonicalMessage =
    canonicalizeRaw(value.canonicalText)

  private def canonicalizeRaw(raw: String): CanonicalMessage = {
    val normalized = MessageCanonicalizer.normalizeWhitespace(raw)
    val body = if (lowercase) normalized.toLowerCase else normalized
    val kind = if (body.isEmpty) MessageKind.Empty else MessageKind.Text
    CanonicalMessage(body = body, kind = kind)
  }
}

final class MetricCanonicalizer(precision: Int = 2) extends BaseCanonicalizer[BigDecimal] {
  override def canonicalize(value: BigDecimal): CanonicalMessage =
    MessageCanonicalizer.metricMessage(value, precision, "BigDecimal")

  def canonicalize(value: Int): CanonicalMessage =
    MessageCanonicalizer.metricMessage(BigDecimal(value), precision, "Int")

  def canonicalize(value: Long): CanonicalMessage =
    MessageCanonicalizer.metricMessage(BigDecimal(value), precision, "Long")

  def canonicalize(value: Double): CanonicalMessage =
    MessageCanonicalizer.metricMessage(BigDecimal.decimal(value), precision, "Double")

  def canonicalize(value: Float): CanonicalMessage =
    MessageCanonicalizer.metricMessage(BigDecimal.decimal(value.toDouble), precision, "Float")
}

final class StructuredCanonicalizer(precision: Int = 2)
    extends BaseCanonicalizer[scala.collection.Map[String, Any]] {

  override def canonicalize(value: scala.collection.Map[String, Any]): CanonicalMessage = {
    val fields = value.iterator
      .collect {
        case (key, item) if !MessageCanonicalizer.metadataKeys.contains(key) =>
          MessageCanonicalizer.renderValue(item, precision).map(MessageCanonicalizer.normalizeToken(key) -> _)
      }
      .flatten
      .toVector
      .sortBy(_._1)

    val body =
      if (fields.isEmpty) ""
      else fields.map { case (key, rendered) => s"$key:$rendered" }.mkString("{", ",", "}")

    val kind = if (fields.isEmpty) MessageKind.Empty else MessageKind.Event

    CanonicalMessage(
      body = body,
      kind = kind,
      channel = MessageCanonicalizer.normalizeChannel(value.get("channel")),
      tags = MessageCanonicalizer.normalizeTags(value.get("tags")),
      attributes = Map("field_count" -> fields.size.toString),
      observedAt = MessageCanonicalizer.normalizeObservedAt(value.get("observed_at"))
    )
  }
}

final class MessagePipeline(
  processors: Seq[MessageProcessor] = Vector.empty,
  textCanonicalizer: TextCanonicalizer = new TextCanonicalizer(),
  metricCanonicalizer: MetricCanonicalizer = new MetricCanonicalizer(),
  structuredCanonicalizer: StructuredCanonicalizer = new StructuredCanonicalizer()
) {
  def canonicalizeMessage(value: Any): CanonicalMessage = {
    val canonical = value match {
      case None => CanonicalMessage("", MessageKind.Empty)
      case message: CanonicalMessage => message
      case Some(inner) => canonicalizeMessage(inner)
      case textLike: MessageLike => textCanonicalizer.canonicalize(textLike)
      case bytes: Array[Byte] => textCanonicalizer.canonicalize(bytes)
      case text: String => textCanonicalizer.canonicalize(text)
      case map: scala.collection.Map[_, _] =>
        val stringKeyed = map.collect { case (key: String, item) => key -> item }.toMap
        structuredCanonicalizer.canonicalize(stringKeyed)
      case decimal: BigDecimal => metricCanonicalizer.canonicalize(decimal)
      case intValue: Int => metricCanonicalizer.canonicalize(intValue)
      case longValue: Long => metricCanonicalizer.canonicalize(longValue)
      case doubleValue: Double => metricCanonicalizer.canonicalize(doubleValue)
      case floatValue: Float => metricCanonicalizer.canonicalize(floatValue)
      case other => textCanonicalizer.canonicalize(other.toString)
    }

    processors.foldLeft(canonical) { (message, processor) => processor.process(message) }
  }

  def run(values: Iterable[Any]): Vector[CanonicalMessage] =
    values.iterator.map(canonicalizeMessage).toVector
}

object MessageCanonicalizer {
  private val TimestampFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss")

  val metadataKeys: Set[String] = Set("channel", "tags", "observed_at")

  def normalizeWhitespace(value: String): String =
    value.trim.split("\\s+").filter(_.nonEmpty).mkString(" ")

  def normalizeToken(value: String): String =
    normalizeWhitespace(value).toLowerCase

  def normalizeChannel(value: Any): Option[String] = value match {
    case None => None
    case Some(inner) => normalizeChannel(inner)
    case other =>
      Option(normalizeToken(other.toString)).filter(_.nonEmpty)
  }

  def normalizeTags(value: Any): Vector[String] = value match {
    case None => Vector.empty
    case Some(inner) => normalizeTags(inner)
    case seq: Iterable[_] =>
      seq.iterator
        .map(item => normalizeToken(item.toString))
        .filter(_.nonEmpty)
        .toVector
        .distinct
        .sorted
    case other =>
      Vector(normalizeToken(other.toString)).filter(_.nonEmpty)
  }

  def normalizeObservedAt(value: Any): Option[String] = value match {
    case None => None
    case Some(inner) => normalizeObservedAt(inner)
    case dateTime: LocalDateTime => Some(dateTime.format(TimestampFormatter))
    case other =>
      Option(normalizeWhitespace(other.toString)).filter(_.nonEmpty)
  }

  def formatMetric(value: BigDecimal, precision: Int, integral: Boolean = false): String =
    if (integral) value.bigDecimal.toPlainString
    else {
      val rounded = value.setScale(precision, RoundingMode.HALF_UP).bigDecimal.stripTrailingZeros()
      val rendered = rounded.toPlainString
      if (rendered == "-0") "0" else rendered
    }

  def metricMessage(value: BigDecimal, precision: Int, sourceType: String): CanonicalMessage = {
    val integralTypes = Set("Int", "Long")
    CanonicalMessage(
      body = formatMetric(value, precision, integralTypes.contains(sourceType)),
      kind = MessageKind.Metric,
      channel = Some("metrics"),
      attributes = Map("source_type" -> sourceType)
    )
  }

  def renderValue(value: Any, precision: Int): Option[String] = value match {
    case None => None
    case Some(inner) => renderValue(inner, precision)
    case booleanValue: Boolean => Some(booleanValue.toString)
    case intValue: Int => Some(intValue.toString)
    case longValue: Long => Some(longValue.toString)
    case decimal: BigDecimal => Some(formatMetric(decimal, precision))
    case doubleValue: Double => Some(formatMetric(BigDecimal.decimal(doubleValue), precision))
    case floatValue: Float => Some(formatMetric(BigDecimal.decimal(floatValue.toDouble), precision))
    case dateTime: LocalDateTime => Some(dateTime.format(TimestampFormatter))
    case map: scala.collection.Map[_, _] =>
      val renderedFields = map.iterator
        .collect { case (key, item) => renderValue(item, precision).map(normalizeToken(key.toString) -> _) }
        .flatten
        .toVector
        .sortBy(_._1)

      Some(renderedFields.map { case (key, item) => s"$key:$item" }.mkString("{", ",", "}"))
    case seq: Iterable[_] =>
      val renderedItems = seq.iterator.flatMap(item => renderValue(item, precision)).toVector
      Some(renderedItems.mkString("[", ",", "]"))
    case textLike: MessageLike => Option(normalizeWhitespace(textLike.canonicalText)).filter(_.nonEmpty)
    case other => Option(normalizeWhitespace(other.toString)).filter(_.nonEmpty)
  }

  def canonicalizeMessage(
    value: Any,
    processors: Seq[MessageProcessor] = Vector.empty
  ): CanonicalMessage =
    new MessagePipeline(processors = processors).canonicalizeMessage(value)

  def canonicalizeBatch(
    values: Iterable[Any],
    processors: Seq[MessageProcessor] = Vector.empty
  ): Vector[CanonicalMessage] =
    new MessagePipeline(processors = processors).run(values)

  def summarizeByKind(messages: Iterable[CanonicalMessage]): Map[String, Int] =
    messages.foldLeft(Map.empty[String, Int].withDefaultValue(0)) { (summary, message) =>
      summary.updated(message.kind.value, summary(message.kind.value) + 1)
    }.toMap
}
EOF
