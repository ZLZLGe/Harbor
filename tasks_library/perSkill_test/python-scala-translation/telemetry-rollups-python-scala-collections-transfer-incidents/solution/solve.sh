#!/bin/bash

set -euo pipefail

cat <<'EOF' > /root/TelemetryIncidentRollups.scala
import java.time.{Duration, Instant}
import scala.io.Source

object TelemetryIncidentRollups {
  final case class AlertRecord(
    service: String,
    severity: String,
    startedAt: Instant,
    endedAt: Instant,
    source: String,
    alertCode: String
  )

  final case class WindowRule(
    mergeGapMinutes: Int,
    pageThreshold: Int,
    summaryPrefix: String
  )

  final case class WindowConfig(
    defaultMergeGapMinutes: Int,
    severityRank: List[String],
    rulesByService: Map[String, WindowRule]
  )

  final case class IncidentSummary(
    service: String,
    severity: String,
    startedAt: String,
    endedAt: String,
    durationMinutes: Long,
    alertCount: Int,
    sourceCount: Int,
    sources: List[String],
    alertCodes: List[String],
    page: Boolean,
    summary: String
  )

  private val DefaultPageThreshold = 2
  private val DefaultSummaryPrefix = "observe"

  def loadAlerts(path: String): List[AlertRecord] = {
    val source = Source.fromFile(path, "UTF-8")
    try {
      val lines = source.getLines().toList
      if (lines.isEmpty) {
        Nil
      } else {
        val header = lines.head.split(",", -1).map(_.trim).toList
        lines.tail.filter(_.trim.nonEmpty).map { line =>
          val row = header.zip(line.split(",", -1).map(_.trim)).toMap.withDefaultValue("")
          AlertRecord(
            service = normalizeLower(row("service")),
            severity = normalizeLower(row("severity")),
            startedAt = Instant.parse(row("started_at").trim),
            endedAt = Instant.parse(row("ended_at").trim),
            source = normalizeLower(row("source")),
            alertCode = row("alert_code").trim.toUpperCase
          )
        }
      }
    } finally {
      source.close()
    }
  }

  def loadWindowConfig(path: String): WindowConfig = {
    val source = Source.fromFile(path, "UTF-8")
    try {
      var defaultMergeGapMinutes = 0
      var severityRank = List.empty[String]
      var currentSection: Option[String] = None
      var sectionValues = Map.empty[String, Map[String, String]]

      source.getLines().foreach { rawLine =>
        val line = rawLine.trim
        if (line.nonEmpty && !line.startsWith("#")) {
          if (line.startsWith("[") && line.endsWith("]")) {
            val sectionName = normalizeLower(line.drop(1).dropRight(1))
            currentSection = Some(sectionName)
            sectionValues = sectionValues.updated(sectionName, sectionValues.getOrElse(sectionName, Map.empty))
          } else {
            val parts = line.split("=", 2)
            if (parts.length == 2) {
              val key = normalizeLower(parts(0))
              val value = parts(1).trim
              currentSection match {
                case None =>
                  key match {
                    case "default_merge_gap_minutes" => defaultMergeGapMinutes = value.toInt
                    case "severity_rank" =>
                      severityRank = value.split(",").toList.map(normalizeLower).filter(_.nonEmpty)
                    case _ =>
                  }
                case Some(sectionName) =>
                  val updated = sectionValues.getOrElse(sectionName, Map.empty) + (key -> value)
                  sectionValues = sectionValues.updated(sectionName, updated)
              }
            }
          }
        }
      }

      val rulesByService = sectionValues.map { case (service, values) =>
        service -> WindowRule(
          mergeGapMinutes = values.getOrElse("merge_gap_minutes", defaultMergeGapMinutes.toString).toInt,
          pageThreshold = values.getOrElse("page_threshold", DefaultPageThreshold.toString).toInt,
          summaryPrefix = values.getOrElse("summary_prefix", DefaultSummaryPrefix).trim
        )
      }

      WindowConfig(
        defaultMergeGapMinutes = defaultMergeGapMinutes,
        severityRank = severityRank,
        rulesByService = rulesByService
      )
    } finally {
      source.close()
    }
  }

  def rollupIncidents(
    alerts: Seq[AlertRecord],
    config: WindowConfig
  ): List[IncidentSummary] = {
    val incidents = alerts
      .groupBy(alert => (alert.service, alert.severity))
      .toList
      .flatMap { case ((service, severity), bucket) =>
        val rule = ruleFor(service, config)
        val sortedBucket = bucket.toList.sortBy(alert =>
          (
            alert.startedAt.toEpochMilli,
            alert.endedAt.toEpochMilli,
            alert.source,
            alert.alertCode
          )
        )

        if (sortedBucket.isEmpty) {
          Nil
        } else {
          val first = sortedBucket.head
          val merged = sortedBucket.tail.foldLeft(
            List(newMutableIncident(first.startedAt, first.endedAt, Set(first.source), Set(first.alertCode), 1))
          ) { (acc, alert) =>
            val current = acc.last
            val mergeBoundary = current.endedAt.plusSeconds(rule.mergeGapMinutes.toLong * 60L)
            if (!alert.startedAt.isAfter(mergeBoundary)) {
              acc.init :+ current.copy(
                endedAt = if (alert.endedAt.isAfter(current.endedAt)) alert.endedAt else current.endedAt,
                sources = current.sources + alert.source,
                alertCodes = current.alertCodes + alert.alertCode,
                alertCount = current.alertCount + 1
              )
            } else {
              acc :+ newMutableIncident(
                alert.startedAt,
                alert.endedAt,
                Set(alert.source),
                Set(alert.alertCode),
                1
              )
            }
          }

          merged.map(toIncidentSummary(service, severity, rule, _))
        }
      }

    val severityOrder = config.severityRank.zipWithIndex.toMap
    incidents.sortBy { incident =>
      val rank = severityOrder.get(incident.severity)
      (
        incident.service,
        if (rank.isDefined) 0 else 1,
        rank.getOrElse(Int.MaxValue),
        if (rank.isDefined) "" else incident.severity,
        incident.startedAt,
        incident.endedAt
      )
    }
  }

  def buildServiceDigest(
    incidents: Seq[IncidentSummary],
    severityRank: Seq[String]
  ): List[String] = {
    val rankMap = severityRank.zipWithIndex.toMap

    incidents
      .groupBy(_.service)
      .toList
      .map { case (service, serviceIncidents) =>
        val incidentCount = serviceIncidents.size
        val pagedCount = serviceIncidents.count(_.page)
        val severityParts = serviceIncidents
          .groupBy(_.severity)
          .toList
          .sortBy { case (severity, _) =>
            val rank = rankMap.get(severity)
            (if (rank.isDefined) 0 else 1, rank.getOrElse(Int.MaxValue), if (rank.isDefined) "" else severity)
          }
          .map { case (severity, rows) => s"$severity:${rows.size}" }

        val sources = serviceIncidents.flatMap(_.sources).distinct.sorted
        (
          -pagedCount,
          -incidentCount,
          service,
          s"SERVICE|$service|$incidentCount|$pagedCount|${joinOrDash(severityParts)}|${joinOrDash(sources)}"
        )
      }
      .sortBy { case (negPagedCount, negIncidentCount, service, _) =>
        (negPagedCount, negIncidentCount, service)
      }
      .map(_._4)
  }

  def renderIncidentLines(incidents: Seq[IncidentSummary]): List[String] =
    incidents.toList.map { incident =>
      s"INCIDENT|${incident.service}|${incident.severity}|${incident.startedAt}|${incident.endedAt}|${incident.durationMinutes}|${incident.alertCount}|${incident.sourceCount}|${joinOrDash(incident.sources)}|${joinOrDash(incident.alertCodes)}|${incident.page}|${incident.summary}"
    }

  private final case class MutableIncident(
    startedAt: Instant,
    endedAt: Instant,
    sources: Set[String],
    alertCodes: Set[String],
    alertCount: Int
  )

  private def newMutableIncident(
    startedAt: Instant,
    endedAt: Instant,
    sources: Set[String],
    alertCodes: Set[String],
    alertCount: Int
  ): MutableIncident =
    MutableIncident(
      startedAt = startedAt,
      endedAt = endedAt,
      sources = sources,
      alertCodes = alertCodes,
      alertCount = alertCount
    )

  private def toIncidentSummary(
    service: String,
    severity: String,
    rule: WindowRule,
    incident: MutableIncident
  ): IncidentSummary = {
    val sortedSources = incident.sources.toList.sorted
    val sortedCodes = incident.alertCodes.toList.sorted
    val startedAt = incident.startedAt.toString
    val endedAt = incident.endedAt.toString
    val sourceCount = sortedSources.size
    val page = severity == "critical" || sourceCount >= rule.pageThreshold
    val summary =
      s"${rule.summaryPrefix}|$service|$severity|$startedAt|$endedAt|${joinOrDash(sortedSources)}|${joinOrDash(sortedCodes)}|${incident.alertCount}"

    IncidentSummary(
      service = service,
      severity = severity,
      startedAt = startedAt,
      endedAt = endedAt,
      durationMinutes = Duration.between(incident.startedAt, incident.endedAt).toMinutes,
      alertCount = incident.alertCount,
      sourceCount = sourceCount,
      sources = sortedSources,
      alertCodes = sortedCodes,
      page = page,
      summary = summary
    )
  }

  private def ruleFor(service: String, config: WindowConfig): WindowRule =
    config.rulesByService.getOrElse(
      service,
      WindowRule(
        mergeGapMinutes = config.defaultMergeGapMinutes,
        pageThreshold = DefaultPageThreshold,
        summaryPrefix = DefaultSummaryPrefix
      )
    )

  private def joinOrDash(values: Seq[String]): String =
    if (values.isEmpty) "-" else values.mkString(",")

  private def normalizeLower(value: String): String =
    value.trim.toLowerCase
}
EOF
