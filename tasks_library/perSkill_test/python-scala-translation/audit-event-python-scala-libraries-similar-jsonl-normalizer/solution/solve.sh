#!/bin/bash
set -e

cat <<'EOF' > /root/EventNormalizer.scala
package eventnormalizer

import io.circe.Encoder
import io.circe.generic.semiauto._
import io.circe.parser.parse
import io.circe.syntax._

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths}
import java.time._
import java.time.format.DateTimeFormatter

import scala.collection.mutable
import scala.io.Source
import scala.util.Using
import scala.util.matching.Regex

final case class AuditEvent(
  eventId: String,
  timestamp: String,
  actor: String,
  action: String,
  resource: String,
  severity: String,
  labels: List[String],
  metadata: Map[String, String]
) {
  def toJsonLine: String = this.asJson.noSpaces
}

object AuditEvent {
  implicit val encoder: Encoder[AuditEvent] = deriveEncoder[AuditEvent]
}

final case class EventSummary(
  total: Int,
  bySeverity: Map[String, Int],
  byActor: Map[String, Int],
  labelCounts: Map[String, Int],
  windowStart: String,
  windowEnd: String
)

object EventSummary {
  implicit val encoder: Encoder[EventSummary] = deriveEncoder[EventSummary]
}

final class EventNormalizer(val baseDir: Path = Paths.get(".")) {

  private val isoOutputFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'").withZone(ZoneOffset.UTC)
  private val localTimestampFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
  private val slashOffsetFormatter = DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss Z")
  private val labelPattern: Regex = """#([A-Za-z0-9_-]+)""".r
  private val highPattern: Regex = """(?i)(delete|drop|disable|revoke)""".r
  private val mediumPattern: Regex = """(?i)(write|update|patch|rotate|change)""".r

  private def attempt[A](thunk: => A): Option[A] =
    try {
      Some(thunk)
    } catch {
      case _: Exception => None
    }

  private def resolvePath(relativePath: String): Path = {
    val path = Paths.get(relativePath)
    if (path.isAbsolute) path else baseDir.resolve(path).normalize()
  }

  private def readPath(json: io.circe.Json, path: List[String]): Option[String] = {
    val finalJson = path.foldLeft(Option(json)) { (cursor, key) =>
      cursor.flatMap(_.hcursor.get[io.circe.Json](key).toOption)
    }

    finalJson.flatMap { value =>
      value.asString.map(_.trim).filter(_.nonEmpty).orElse(value.asNumber.map(_.toString))
    }
  }

  private def firstString(json: io.circe.Json, paths: List[List[String]], default: String): String =
    paths.view.flatMap(path => readPath(json, path)).headOption.getOrElse(default)

  private def normalizeAction(value: String): String = {
    val normalized = value.trim.toUpperCase.replaceAll("[^A-Z0-9]+", "_").stripPrefix("_").stripSuffix("_")
    if (normalized.nonEmpty) normalized else "UNKNOWN"
  }

  private def classifySeverity(action: String, message: String): String = {
    val combined = s"$action $message"
    if (highPattern.findFirstIn(combined).nonEmpty) {
      "high"
    } else if (mediumPattern.findFirstIn(combined).nonEmpty) {
      "medium"
    } else {
      "low"
    }
  }

  def normalizeTimestamp(value: String): String = {
    val trimmed = value.trim

    val instant =
      attempt(Instant.parse(trimmed))
        .orElse(attempt(OffsetDateTime.parse(trimmed).toInstant))
        .orElse(attempt(LocalDateTime.parse(trimmed, localTimestampFormatter).toInstant(ZoneOffset.UTC)))
        .orElse(attempt(OffsetDateTime.parse(trimmed, slashOffsetFormatter).toInstant))
        .orElse(attempt(LocalDate.parse(trimmed).atStartOfDay().toInstant(ZoneOffset.UTC)))
        .getOrElse(throw new IllegalArgumentException(s"unsupported timestamp: $value"))

    isoOutputFormatter.format(instant)
  }

  def extractLabels(parts: String*): List[String] = {
    val seen = mutable.LinkedHashSet.empty[String]

    parts.foreach { part =>
      labelPattern.findAllMatchIn(part).foreach { m =>
        seen += m.group(1).toLowerCase
      }
    }

    seen.toList
  }

  def normalizeEvent(payload: io.circe.Json): AuditEvent = {
    val rawTime = firstString(payload, List(List("ts"), List("timestamp"), List("occurred_at")), "1970-01-01T00:00:00Z")
    val actor = firstString(payload, List(List("actor", "email"), List("actor", "name"), List("user"), List("principal")), "unknown")
    val action = normalizeAction(firstString(payload, List(List("action"), List("event"), List("type")), "unknown"))
    val resource = firstString(payload, List(List("resource"), List("resource", "id"), List("target"), List("object")), "unknown")
    val message = firstString(payload, List(List("details"), List("message"), List("note")), "")
    val eventId = firstString(payload, List(List("id"), List("event_id")), s"$rawTime:$actor:$action")
    val source = firstString(payload, List(List("source")), "inline")

    AuditEvent(
      eventId = eventId,
      timestamp = normalizeTimestamp(rawTime),
      actor = actor,
      action = action,
      resource = resource,
      severity = classifySeverity(action, message),
      labels = extractLabels(resource, message),
      metadata = Map("rawTime" -> rawTime, "source" -> source)
    )
  }

  def parseLine(line: String): AuditEvent =
    parse(line).fold(error => throw new IllegalArgumentException(error.message), normalizeEvent)

  def loadEvents(relativePath: String): List[AuditEvent] = {
    val path = resolvePath(relativePath)
    Using.resource(Source.fromFile(path.toFile, "UTF-8")) { source =>
      source.getLines().map(_.trim).filter(_.nonEmpty).map(parseLine).toList
    }
  }

  def summarize(events: Seq[AuditEvent]): EventSummary = {
    val byActor = events.groupBy(_.actor).view.mapValues(_.size).toMap
    val labelCounts = events.flatMap(_.labels).groupBy(identity).view.mapValues(_.size).toMap
    val timestamps = events.map(_.timestamp).sorted

    EventSummary(
      total = events.size,
      bySeverity = Map(
        "low" -> events.count(_.severity == "low"),
        "medium" -> events.count(_.severity == "medium"),
        "high" -> events.count(_.severity == "high")
      ),
      byActor = byActor,
      labelCounts = labelCounts,
      windowStart = timestamps.headOption.getOrElse(""),
      windowEnd = timestamps.lastOption.getOrElse("")
    )
  }

  def normalizeFile(relativeInput: String, relativeOutput: String): EventSummary = {
    val events = loadEvents(relativeInput)
    val outputPath = resolvePath(relativeOutput)

    Option(outputPath.getParent).foreach(parent => Files.createDirectories(parent))
    val content =
      if (events.nonEmpty) events.map(_.toJsonLine).mkString("", System.lineSeparator(), System.lineSeparator())
      else ""

    Files.writeString(outputPath, content, StandardCharsets.UTF_8)
    summarize(events)
  }

  def loadAndSummarize(relativePath: String): EventSummary =
    summarize(loadEvents(relativePath))
}

object EventNormalizer {
  def main(args: Array[String]): Unit = {
    if (args.length != 2) {
      throw new IllegalArgumentException("usage: EventNormalizer <input-jsonl> <output-jsonl>")
    }

    val summary = new EventNormalizer().normalizeFile(args(0), args(1))
    println(summary.asJson.spaces2)
  }
}
EOF
