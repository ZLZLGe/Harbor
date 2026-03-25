#!/bin/bash
set -euo pipefail

cat <<'EOF' > /root/AccessLogAnalyzer.scala
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths}
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.time.{Instant, ZoneOffset, ZonedDateTime}
import java.util.Locale

import scala.collection.mutable
import scala.io.Source
import scala.util.Try

final case class SessionSummary(
  sessionId: String,
  clientId: String,
  userId: String,
  sessionStartUtc: String,
  sessionEndUtc: String,
  durationMinutes: Int,
  requestCount: Int,
  status2xx: Int,
  status4xx: Int,
  status5xx: Int,
  totalBytes: Int,
  paths: String
)

object AccessLogAnalyzer {
  private final case class LogEntry(
    clientId: String,
    userId: String,
    occurredAt: Instant,
    path: String,
    status: Int,
    byteCount: Int
  )

  private val logPattern =
    raw"""^\[([^\]]+)\]\s+client=([A-Za-z0-9-]+)\s+user=([A-Za-z0-9_-]+)\s+method=([A-Z]+)\s+path=(\S+)\s+status=(\d{3})\s+bytes=(\d+)$$""".r

  private val apacheFormatter =
    DateTimeFormatter.ofPattern("dd/MMM/yyyy:HH:mm:ss Z", Locale.ENGLISH)

  private val isoFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssZ")

  private val utcFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'").withZone(ZoneOffset.UTC)

  private val csvColumns = Vector(
    "session_id",
    "client_id",
    "user_id",
    "session_start_utc",
    "session_end_utc",
    "duration_minutes",
    "request_count",
    "status_2xx",
    "status_4xx",
    "status_5xx",
    "total_bytes",
    "paths"
  )

  private def parseTimestamp(raw: String): Instant = {
    val text = raw.trim
    val attempts = Vector(
      Try(ZonedDateTime.parse(text, apacheFormatter).toInstant),
      Try(ZonedDateTime.parse(text, isoFormatter).toInstant)
    )
    attempts.collectFirst { case scala.util.Success(value) => value }
      .getOrElse(throw new IllegalArgumentException(s"unsupported timestamp: $raw"))
  }

  private def formatUtc(value: Instant): String =
    utcFormatter.format(value)

  private def parseLine(rawLine: String): LogEntry = rawLine.trim match {
    case logPattern(timestamp, clientId, userId, _, path, status, byteCount) =>
      LogEntry(
        clientId = clientId,
        userId = userId,
        occurredAt = parseTimestamp(timestamp),
        path = path,
        status = status.toInt,
        byteCount = byteCount.toInt
      )
    case _ =>
      throw new IllegalArgumentException(s"invalid log line: $rawLine")
  }

  private def loadEntries(inputPath: Path): Vector[LogEntry] =
    Source.fromFile(inputPath.toFile, StandardCharsets.UTF_8.name()).getLines().toVector.collect {
      case line if line.trim.nonEmpty && !line.trim.startsWith("#") => parseLine(line)
    }

  private def summarizeSession(
    clientId: String,
    userId: String,
    sessionIndex: Int,
    entries: Vector[LogEntry]
  ): SessionSummary = {
    val first = entries.head
    val last = entries.last
    val uniquePaths = entries.iterator.map(_.path).toSet.toVector.sorted.mkString("|")

    SessionSummary(
      sessionId = f"$clientId:$userId:s$sessionIndex%02d",
      clientId = clientId,
      userId = userId,
      sessionStartUtc = formatUtc(first.occurredAt),
      sessionEndUtc = formatUtc(last.occurredAt),
      durationMinutes = ChronoUnit.MINUTES.between(first.occurredAt, last.occurredAt).toInt,
      requestCount = entries.size,
      status2xx = entries.count(entry => entry.status >= 200 && entry.status < 300),
      status4xx = entries.count(entry => entry.status >= 400 && entry.status < 500),
      status5xx = entries.count(entry => entry.status >= 500 && entry.status < 600),
      totalBytes = entries.map(_.byteCount).sum,
      paths = uniquePaths
    )
  }

  def analyze(inputPath: Path, sessionGapMinutes: Int): Seq[SessionSummary] = {
    val grouped = loadEntries(inputPath).groupBy(entry => (entry.clientId, entry.userId))

    val summaries = grouped.toVector.flatMap { case ((clientId, userId), entries) =>
      val ordered = entries.sortBy(entry => (entry.occurredAt.toEpochMilli, entry.path, entry.status))
      val sessions = mutable.ListBuffer.empty[Vector[LogEntry]]
      val current = mutable.ArrayBuffer.empty[LogEntry]
      var sessionIndex = 1

      ordered.foreach { entry =>
        if (current.isEmpty) {
          current += entry
        } else {
          val gapMinutes = ChronoUnit.MINUTES.between(current.last.occurredAt, entry.occurredAt).toInt
          if (gapMinutes > sessionGapMinutes) {
            sessions += current.toVector
            current.clear()
            sessionIndex += 1
          }
          current += entry
        }
      }

      if (current.nonEmpty) {
        sessions += current.toVector
      }

      sessions.zipWithIndex.map { case (sessionEntries, index) =>
        summarizeSession(clientId, userId, index + 1, sessionEntries)
      }
    }

    summaries.sortBy(summary => (summary.sessionStartUtc, summary.sessionId))
  }

  private def csvEscape(value: String): String = {
    if (value.exists(ch => ch == ',' || ch == '"' || ch == '\n' || ch == '\r')) {
      "\"" + value.replace("\"", "\"\"") + "\""
    } else {
      value
    }
  }

  private def writeCsv(summaries: Seq[SessionSummary], outputPath: Path): Unit = {
    Files.createDirectories(outputPath.getParent)
    val rows = summaries.map { summary =>
      Vector(
        summary.sessionId,
        summary.clientId,
        summary.userId,
        summary.sessionStartUtc,
        summary.sessionEndUtc,
        summary.durationMinutes.toString,
        summary.requestCount.toString,
        summary.status2xx.toString,
        summary.status4xx.toString,
        summary.status5xx.toString,
        summary.totalBytes.toString,
        summary.paths
      ).map(csvEscape).mkString(",")
    }

    val content = (csvColumns.mkString(",") +: rows).mkString("", "\n", "\n")
    Files.writeString(outputPath, content, StandardCharsets.UTF_8)
  }

  def run(inputPath: Path, outputPath: Path, sessionGapMinutes: Int): Unit =
    writeCsv(analyze(inputPath, sessionGapMinutes), outputPath)

  def main(args: Array[String]): Unit =
    run(
      Paths.get("/root/challenge/input/access.log"),
      Paths.get("/root/challenge/output/session_summary.csv"),
      30
    )
}
EOF
