import java.time.Instant

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

  def loadAlerts(path: String): List[AlertRecord] = {
    val lines = scala.io.Source.fromFile(path, "UTF-8").getLines().toList
    val header = lines.head.split(",", -1).map(_.trim)
    lines.tail.filter(_.trim.nonEmpty).map { line =>
      val values = line.split(",", -1).map(_.trim)
      val row = header.zip(values).toMap
      AlertRecord(
        service = row("service").toLowerCase,
        severity = row("severity").toLowerCase,
        startedAt = Instant.parse(row("started_at")),
        endedAt = Instant.parse(row("ended_at")),
        source = row("source").toLowerCase,
        alertCode = row("alert_code").toUpperCase
      )
    }
  }

  def loadWindowConfig(path: String): WindowConfig = {
    // TODO: parse the INI-like config file instead of returning placeholders.
    WindowConfig(
      defaultMergeGapMinutes = 0,
      severityRank = Nil,
      rulesByService = Map.empty
    )
  }

  def rollupIncidents(
    alerts: Seq[AlertRecord],
    config: WindowConfig
  ): List[IncidentSummary] = {
    // TODO: merge alert windows by (service, severity) and compute incident summaries.
    ???
  }

  def buildServiceDigest(
    incidents: Seq[IncidentSummary],
    severityRank: Seq[String]
  ): List[String] = {
    // TODO: group by service and format summary lines.
    ???
  }

  def renderIncidentLines(incidents: Seq[IncidentSummary]): List[String] =
    incidents.toList.map { incident =>
      val sources = if (incident.sources.isEmpty) "-" else incident.sources.mkString(",")
      val codes = if (incident.alertCodes.isEmpty) "-" else incident.alertCodes.mkString(",")
      s"INCIDENT|${incident.service}|${incident.severity}|${incident.startedAt}|${incident.endedAt}|${incident.durationMinutes}|${incident.alertCount}|${incident.sourceCount}|$sources|$codes|${incident.page}|${incident.summary}"
    }
}
