#!/bin/bash
set -e

cat <<'EOF' > /root/EventNormalizer.scala
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths}
import java.time.{LocalDateTime, OffsetDateTime, ZoneOffset}
import java.time.format.DateTimeFormatter

import io.circe.{Encoder, Json, Printer}
import io.circe.generic.semiauto.deriveEncoder
import io.circe.parser.parse
import io.circe.syntax.EncoderOps

import scala.io.Source
import scala.util.Using
import scala.util.matching.Regex

final case class NormalizedEvent(
  id: String,
  occurred_at: String,
  event_type: String,
  actor: String,
  metadata: Map[String, String]
)

object EventNormalizer {
  private val detailPattern: Regex = """([a-z_]+)\s*=\s*([^;]+)""".r
  private val aliasMap: Map[String, String] = Map(
    "login" -> "user_login",
    "login_success" -> "user_login",
    "signin" -> "user_login",
    "sign_in" -> "user_login",
    "checkout_complete" -> "order_completed",
    "order_placed" -> "order_completed",
    "purchase" -> "order_completed",
    "password_reset" -> "password_reset",
    "session_timeout" -> "session_timeout"
  )
  private val utcOutputFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'")
  private val isoFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssX")
  private val utcTextFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ssX")
  private val offsetFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ssXX")
  private val slashOffsetFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss XX")
  private val dayFirstFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("dd-MM-yyyy HH:mm:ss")
  private val printer: Printer = Printer.spaces2SortKeys

  implicit private val normalizedEventEncoder: Encoder[NormalizedEvent] = deriveEncoder[NormalizedEvent]

  private def parseOffsetTimestamp(text: String): Option[OffsetDateTime] = {
    val attempts = List(
      () => OffsetDateTime.parse(text, isoFormatter),
      () => OffsetDateTime.parse(text, utcTextFormatter),
      () => OffsetDateTime.parse(text, offsetFormatter),
      () => OffsetDateTime.parse(text, slashOffsetFormatter)
    )
    attempts.view.map { attempt =>
      scala.util.Try(attempt()).toOption
    }.collectFirst { case Some(value) => value }
  }

  private def parseUtcLocalTimestamp(text: String): Option[OffsetDateTime] = {
    scala.util.Try(LocalDateTime.parse(text, dayFirstFormatter).atOffset(ZoneOffset.UTC)).toOption
  }

  def normalizeTimestamp(raw: String): String = {
    val text = raw.trim
    val parsed = parseOffsetTimestamp(text).orElse(parseUtcLocalTimestamp(text)).getOrElse {
      throw new IllegalArgumentException(s"unsupported timestamp: $raw")
    }
    parsed
      .withOffsetSameInstant(ZoneOffset.UTC)
      .format(utcOutputFormatter)
  }

  def canonicalEventType(raw: String): String = {
    val cleaned = raw.trim.toLowerCase.replaceAll("[^a-z0-9]+", "_").stripPrefix("_").stripSuffix("_")
    aliasMap.getOrElse(cleaned, cleaned)
  }

  def normalizeActor(raw: String): String =
    raw.trim.toLowerCase.replaceAll("\\s+", " ")

  def parseMetadata(details: Option[String]): Map[String, String] =
    details.toList.flatMap { text =>
      detailPattern.findAllMatchIn(text).map { matched =>
        matched.group(1).toLowerCase -> matched.group(2).trim
      }
    }.toMap

  private def requiredField(raw: Json, primary: String, fallback: Option[String] = None): String =
    raw.hcursor.get[String](primary).toOption
      .orElse(fallback.flatMap(name => raw.hcursor.get[String](name).toOption))
      .map(_.trim)
      .getOrElse(throw new IllegalArgumentException(s"missing field: $primary"))

  def normalizeEvent(raw: Json): NormalizedEvent = {
    val id = requiredField(raw, "event_id")
    val timestamp = requiredField(raw, "occurred_at", Some("timestamp"))
    val eventType = requiredField(raw, "event_name", Some("kind"))
    val actor = requiredField(raw, "user", Some("actor"))
    val details = raw.hcursor.get[String]("details").toOption

    NormalizedEvent(
      id = id,
      occurred_at = normalizeTimestamp(timestamp),
      event_type = canonicalEventType(eventType),
      actor = normalizeActor(actor),
      metadata = parseMetadata(details)
    )
  }

  def loadEvents(inputPath: Path): List[Json] =
    Using.resource(Source.fromFile(inputPath.toFile, "UTF-8")) { source =>
      source.getLines().toList.filter(_.trim.nonEmpty).map { line =>
        parse(line).fold(error => throw error, identity)
      }
    }

  def buildReport(inputPath: Path): Json = {
    val normalized = loadEvents(inputPath)
      .map(normalizeEvent)
      .sortBy(event => (event.occurred_at, event.id))

    val byType = normalized
      .groupMapReduce(_.event_type)(_ => 1)(_ + _)
      .toList
      .sortBy(_._1)

    val actors = normalized.map(_.actor).distinct.sorted

    Json.obj(
      "total_events" -> Json.fromInt(normalized.size),
      "by_type" -> Json.obj(byType.map { case (eventType, count) =>
        eventType -> Json.fromInt(count)
      }: _*),
      "actors" -> Json.arr(actors.map(Json.fromString): _*),
      "normalized_events" -> Json.arr(normalized.map(_.asJson): _*)
    )
  }

  def writeReport(report: Json, outputPath: Path): Unit = {
    Option(outputPath.getParent).foreach(parent => Files.createDirectories(parent))
    Files.writeString(outputPath, printer.print(report) + "\n", StandardCharsets.UTF_8)
  }

  def run(inputPath: Path, outputPath: Path): Unit =
    writeReport(buildReport(inputPath), outputPath)

  def main(args: Array[String]): Unit =
    run(
      Paths.get("/root/challenge/input/events.jsonl"),
      Paths.get("/root/challenge/output/daily_report.json")
    )
}
EOF
