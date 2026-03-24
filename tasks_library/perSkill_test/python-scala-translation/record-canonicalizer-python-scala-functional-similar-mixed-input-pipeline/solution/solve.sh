#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/RecordCanonicalizer.scala
import java.nio.charset.StandardCharsets
import java.time.{LocalDate, LocalDateTime}
import java.time.format.DateTimeFormatter

trait CanonicalValue {
  def canonicalValue: String
}

sealed trait FieldKind {
  def entryName: String
}

object FieldKind {
  case object Text extends FieldKind { val entryName = "text" }
  case object Number extends FieldKind { val entryName = "number" }
  case object Temporal extends FieldKind { val entryName = "temporal" }
  case object Flag extends FieldKind { val entryName = "flag" }
  case object Structured extends FieldKind { val entryName = "structured" }
  case object Empty extends FieldKind { val entryName = "empty" }

  val values: Vector[FieldKind] = Vector(Text, Number, Temporal, Flag, Structured, Empty)
}

final case class CanonicalField(
  key: String,
  value: String,
  kind: FieldKind,
  metadata: Map[String, Any] = Map.empty
) {
  def withMetadata(entries: (String, Any)*): CanonicalField =
    copy(metadata = metadata ++ entries.toMap)
}

abstract class BaseCanonicalizer[A] {
  def canonicalize(key: String, value: A, metadata: Map[String, Any] = Map.empty): CanonicalField

  def canonicalizeBatch(entries: Iterable[(String, A)], metadata: Map[String, Any] = Map.empty): Iterator[CanonicalField] =
    entries.iterator.map { case (key, value) => canonicalize(key, value, metadata) }
}

final class TextCanonicalizer(
  keyNormalizer: String => String = identity,
  valueNormalizer: String => String = identity,
  encoding: String = "UTF-8"
) extends BaseCanonicalizer[Any] {
  override def canonicalize(key: String, value: Any, metadata: Map[String, Any] = Map.empty): CanonicalField = {
    val text = value match {
      case bytes: Array[Byte] => new String(bytes, encoding)
      case string: String => string
      case other => other.toString
    }

    CanonicalField(keyNormalizer(key), valueNormalizer(text), FieldKind.Text, metadata)
  }
}

final class NumericCanonicalizer(
  precision: Int = 2,
  keyNormalizer: String => String = identity
) extends BaseCanonicalizer[Any] {
  private val pattern = s"%.${precision}f"

  override def canonicalize(key: String, value: Any, metadata: Map[String, Any] = Map.empty): CanonicalField = {
    val rendered = value match {
      case number: Byte => number.toString
      case number: Short => number.toString
      case number: Int => number.toString
      case number: Long => number.toString
      case number: BigInt => number.toString
      case number: Float => pattern.format(number.toDouble)
      case number: Double => pattern.format(number)
      case number: BigDecimal => pattern.format(number.toDouble)
      case other => pattern.format(other.toString.toDouble)
    }

    CanonicalField(
      keyNormalizer(key),
      rendered,
      FieldKind.Number,
      metadata + ("original_type" -> value.getClass.getSimpleName)
    )
  }
}

final class TemporalCanonicalizer(
  formatString: Option[String] = None,
  keyNormalizer: String => String = identity
) extends BaseCanonicalizer[Any] {
  private val isoDateTime = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss")
  private val isoDate = DateTimeFormatter.ofPattern("yyyy-MM-dd")

  override def canonicalize(key: String, value: Any, metadata: Map[String, Any] = Map.empty): CanonicalField = {
    val rendered = value match {
      case dateTime: LocalDateTime =>
        dateTime.format(formatString.map(DateTimeFormatter.ofPattern).getOrElse(isoDateTime))
      case date: LocalDate =>
        date.format(formatString.map(DateTimeFormatter.ofPattern).getOrElse(isoDate))
      case other =>
        throw new IllegalArgumentException(s"Unsupported temporal value: ${other.getClass.getName}")
    }

    CanonicalField(keyNormalizer(key), rendered, FieldKind.Temporal, metadata)
  }
}

final class RecordCanonicalizer(
  keyNormalizer: String => String = identity,
  textNormalizer: String => String = identity,
  precision: Int = 2,
  defaultMetadata: Map[String, Any] = Map.empty
) extends BaseCanonicalizer[Any] {
  private val textCanonicalizer = new TextCanonicalizer(keyNormalizer, textNormalizer)
  private val numericCanonicalizer = new NumericCanonicalizer(precision, keyNormalizer)
  private val temporalCanonicalizer = new TemporalCanonicalizer(None, keyNormalizer)

  override def canonicalize(key: String, value: Any, metadata: Map[String, Any] = Map.empty): CanonicalField = {
    val mergedMetadata = defaultMetadata ++ metadata

    value match {
      case null =>
        CanonicalField(keyNormalizer(key), "", FieldKind.Empty, mergedMetadata)
      case None =>
        CanonicalField(keyNormalizer(key), "", FieldKind.Empty, mergedMetadata)
      case bool: Boolean =>
        CanonicalField(keyNormalizer(key), bool.toString.toLowerCase, FieldKind.Flag, mergedMetadata)
      case custom: CanonicalValue =>
        CanonicalField(keyNormalizer(key), custom.canonicalValue, FieldKind.Structured, mergedMetadata)
      case bytes: Array[Byte] =>
        textCanonicalizer.canonicalize(key, bytes, mergedMetadata)
      case text: String =>
        textCanonicalizer.canonicalize(key, text, mergedMetadata)
      case number: Byte =>
        numericCanonicalizer.canonicalize(key, number, mergedMetadata)
      case number: Short =>
        numericCanonicalizer.canonicalize(key, number, mergedMetadata)
      case number: Int =>
        numericCanonicalizer.canonicalize(key, number, mergedMetadata)
      case number: Long =>
        numericCanonicalizer.canonicalize(key, number, mergedMetadata)
      case number: Float =>
        numericCanonicalizer.canonicalize(key, number, mergedMetadata)
      case number: Double =>
        numericCanonicalizer.canonicalize(key, number, mergedMetadata)
      case number: BigDecimal =>
        numericCanonicalizer.canonicalize(key, number, mergedMetadata)
      case number: BigInt =>
        numericCanonicalizer.canonicalize(key, number, mergedMetadata)
      case dateTime: LocalDateTime =>
        temporalCanonicalizer.canonicalize(key, dateTime, mergedMetadata)
      case date: LocalDate =>
        temporalCanonicalizer.canonicalize(key, date, mergedMetadata)
      case values: scala.collection.Map[_, _] =>
        CanonicalField(
          keyNormalizer(key),
          RecordCanonicalizer.renderStructured(values.toList.sortBy(_._1.toString).map {
            case (mapKey, mapValue) => mapKey.toString -> mapValue
          }.toMap),
          FieldKind.Structured,
          mergedMetadata + ("structured" -> true)
        )
      case values: Iterable[_] =>
        CanonicalField(
          keyNormalizer(key),
          RecordCanonicalizer.renderStructured(values.toVector),
          FieldKind.Structured,
          mergedMetadata + ("structured" -> true)
        )
      case other =>
        CanonicalField(keyNormalizer(key), other.toString, FieldKind.Text, mergedMetadata + ("fallback" -> true))
    }
  }

  def canonicalizeRecord(
    record: Iterable[(String, Any)],
    metadataFactory: Option[(String, Any) => Map[String, Any]] = None
  ): Vector[CanonicalField] =
    record.iterator.map { case (key, value) =>
      val metadata = metadataFactory.map(factory => factory(key, value)).getOrElse(Map.empty[String, Any])
      canonicalize(key, value, metadata)
    }.toVector

  def canonicalizeRecords(
    records: Iterator[Iterable[(String, Any)]],
    metadataFactory: Option[(String, Any) => Map[String, Any]] = None,
    batchSize: Int = 2
  ): Iterator[Vector[CanonicalField]] =
    records.grouped(batchSize).map { group =>
      group.iterator.flatMap(record => canonicalizeRecord(record, metadataFactory)).toVector
    }
}

object RecordCanonicalizer {
  def composeNormalizers(normalizers: (String => String)*): String => String =
    normalizers.foldLeft(identity[String] _) { (current, next) => current.andThen(next) }

  def streamTextSegments(text: String): Iterator[(Int, String)] = new Iterator[(Int, String)] {
    private var offset = 0
    private var index = 0
    private var nextValue: Option[(Int, String)] = fetchNext()

    private def fetchNext(): Option[(Int, String)] = {
      while (offset < text.length && text.charAt(offset).isWhitespace) {
        offset += 1
      }

      if (offset >= text.length) {
        None
      } else {
        val start = offset
        while (offset < text.length && !text.charAt(offset).isWhitespace) {
          offset += 1
        }
        val token = text.substring(start, offset)
        val result = index -> token
        index += 1
        Some(result)
      }
    }

    override def hasNext: Boolean = nextValue.nonEmpty

    override def next(): (Int, String) = {
      val current = nextValue.getOrElse(throw new NoSuchElementException("No more text segments"))
      nextValue = fetchNext()
      current
    }
  }

  private def renderStructured(value: Any): String = value match {
    case map: scala.collection.Map[_, _] =>
      map.toVector
        .sortBy(_._1.toString)
        .map { case (key, item) => "\"" + escape(key.toString) + "\":" + renderStructured(item) }
        .mkString("{", ",", "}")
    case items: Iterable[_] =>
      items.iterator.map(renderStructured).mkString("[", ",", "]")
    case text: String =>
      "\"" + escape(text) + "\""
    case bool: Boolean =>
      bool.toString
    case null =>
      "null"
    case other =>
      other.toString
  }

  private def escape(value: String): String =
    value
      .replace("\\", "\\\\")
      .replace("\"", "\\\"")

  def builder(): CanonicalizerBuilder = CanonicalizerBuilder()
}

final case class CanonicalizerBuilder(
  keyNormalizer: String => String = identity,
  textNormalizers: Vector[String => String] = Vector.empty,
  metadata: Map[String, Any] = Map.empty,
  precision: Int = 2
) {
  def withKeyNormalizer(normalizer: String => String): CanonicalizerBuilder =
    copy(keyNormalizer = RecordCanonicalizer.composeNormalizers(keyNormalizer, normalizer))

  def withTextNormalizer(normalizer: String => String): CanonicalizerBuilder =
    copy(textNormalizers = textNormalizers :+ normalizer)

  def withMetadata(entries: (String, Any)*): CanonicalizerBuilder =
    copy(metadata = metadata ++ entries.toMap)

  def withPrecision(value: Int): CanonicalizerBuilder =
    copy(precision = value)

  def build(): RecordCanonicalizer = {
    val textNormalizer =
      if (textNormalizers.isEmpty) identity[String] _
      else RecordCanonicalizer.composeNormalizers(textNormalizers: _*)

    new RecordCanonicalizer(
      keyNormalizer = keyNormalizer,
      textNormalizer = textNormalizer,
      precision = precision,
      defaultMetadata = metadata
    )
  }
}
EOF
