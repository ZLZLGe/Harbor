from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_PAGE_THRESHOLD = 2
DEFAULT_SUMMARY_PREFIX = "observe"


@dataclass(frozen=True)
class AlertRecord:
    service: str
    severity: str
    started_at: datetime
    ended_at: datetime
    source: str
    alert_code: str


@dataclass(frozen=True)
class WindowRule:
    merge_gap_minutes: int
    page_threshold: int
    summary_prefix: str


@dataclass(frozen=True)
class WindowConfig:
    default_merge_gap_minutes: int
    severity_rank: tuple[str, ...]
    rules_by_service: dict[str, WindowRule]


@dataclass(frozen=True)
class IncidentSummary:
    service: str
    severity: str
    started_at: str
    ended_at: str
    duration_minutes: int
    alert_count: int
    source_count: int
    sources: tuple[str, ...]
    alert_codes: tuple[str, ...]
    page: bool
    summary: str


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value.strip(), TIME_FORMAT).replace(tzinfo=timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime(TIME_FORMAT)


def normalize_lower(value: str) -> str:
    return value.strip().lower()


def normalize_code(value: str) -> str:
    return value.strip().upper()


def join_or_dash(values: tuple[str, ...] | list[str]) -> str:
    return ",".join(values) if values else "-"


def load_alerts(path: str) -> list[AlertRecord]:
    rows: list[AlertRecord] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                AlertRecord(
                    service=normalize_lower(row["service"]),
                    severity=normalize_lower(row["severity"]),
                    started_at=parse_timestamp(row["started_at"]),
                    ended_at=parse_timestamp(row["ended_at"]),
                    source=normalize_lower(row["source"]),
                    alert_code=normalize_code(row["alert_code"]),
                )
            )
    return rows


def load_window_config(path: str) -> WindowConfig:
    top_level: dict[str, str] = {}
    sections: dict[str, dict[str, str]] = {}
    current_section: str | None = None

    with open(path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = normalize_lower(line[1:-1])
                sections.setdefault(current_section, {})
                continue
            key, value = [part.strip() for part in line.split("=", 1)]
            if current_section is None:
                top_level[normalize_lower(key)] = value
            else:
                sections[current_section][normalize_lower(key)] = value

    rules = {
        service: WindowRule(
            merge_gap_minutes=int(values["merge_gap_minutes"]),
            page_threshold=int(values["page_threshold"]),
            summary_prefix=values["summary_prefix"].strip(),
        )
        for service, values in sections.items()
    }

    severity_rank = tuple(
        normalize_lower(item)
        for item in top_level["severity_rank"].split(",")
        if item.strip()
    )

    return WindowConfig(
        default_merge_gap_minutes=int(top_level["default_merge_gap_minutes"]),
        severity_rank=severity_rank,
        rules_by_service=rules,
    )


def rule_for(service: str, config: WindowConfig) -> WindowRule:
    return config.rules_by_service.get(
        service,
        WindowRule(
            merge_gap_minutes=config.default_merge_gap_minutes,
            page_threshold=DEFAULT_PAGE_THRESHOLD,
            summary_prefix=DEFAULT_SUMMARY_PREFIX,
        ),
    )


def severity_sort_key(severity: str, severity_rank: tuple[str, ...] | list[str]) -> tuple[int, int, str]:
    if severity in severity_rank:
        return (0, list(severity_rank).index(severity), severity)
    return (1, len(severity_rank), severity)


def finalize_incident(
    service: str,
    severity: str,
    start: datetime,
    end: datetime,
    sources: set[str],
    alert_codes: set[str],
    alert_count: int,
    rule: WindowRule,
) -> IncidentSummary:
    source_list = tuple(sorted(sources))
    code_list = tuple(sorted(alert_codes))
    started_at = format_timestamp(start)
    ended_at = format_timestamp(end)
    source_count = len(source_list)
    page = severity == "critical" or source_count >= rule.page_threshold
    summary = (
        f"{rule.summary_prefix}|{service}|{severity}|{started_at}|{ended_at}|"
        f"{join_or_dash(source_list)}|{join_or_dash(code_list)}|{alert_count}"
    )
    return IncidentSummary(
        service=service,
        severity=severity,
        started_at=started_at,
        ended_at=ended_at,
        duration_minutes=int((end - start).total_seconds() // 60),
        alert_count=alert_count,
        source_count=source_count,
        sources=source_list,
        alert_codes=code_list,
        page=page,
        summary=summary,
    )


def rollup_incidents(alerts: list[AlertRecord], config: WindowConfig) -> list[IncidentSummary]:
    buckets: dict[tuple[str, str], list[AlertRecord]] = {}
    for alert in alerts:
        buckets.setdefault((alert.service, alert.severity), []).append(alert)

    incidents: list[IncidentSummary] = []
    for (service, severity), bucket in buckets.items():
        rule = rule_for(service, config)
        sorted_bucket = sorted(
            bucket,
            key=lambda alert: (
                alert.started_at,
                alert.ended_at,
                alert.source,
                alert.alert_code,
            ),
        )

        current_start: datetime | None = None
        current_end: datetime | None = None
        current_sources: set[str] = set()
        current_codes: set[str] = set()
        current_count = 0

        for alert in sorted_bucket:
            if current_start is None or current_end is None:
                current_start = alert.started_at
                current_end = alert.ended_at
                current_sources = {alert.source}
                current_codes = {alert.alert_code}
                current_count = 1
                continue

            if alert.started_at <= current_end + timedelta(minutes=rule.merge_gap_minutes):
                current_end = max(current_end, alert.ended_at)
                current_sources.add(alert.source)
                current_codes.add(alert.alert_code)
                current_count += 1
            else:
                incidents.append(
                    finalize_incident(
                        service,
                        severity,
                        current_start,
                        current_end,
                        current_sources,
                        current_codes,
                        current_count,
                        rule,
                    )
                )
                current_start = alert.started_at
                current_end = alert.ended_at
                current_sources = {alert.source}
                current_codes = {alert.alert_code}
                current_count = 1

        if current_start is not None and current_end is not None:
            incidents.append(
                finalize_incident(
                    service,
                    severity,
                    current_start,
                    current_end,
                    current_sources,
                    current_codes,
                    current_count,
                    rule,
                )
            )

    return sorted(
        incidents,
        key=lambda incident: (
            incident.service,
            severity_sort_key(incident.severity, config.severity_rank),
            incident.started_at,
            incident.ended_at,
        ),
    )


def render_incident_lines(incidents: list[IncidentSummary]) -> list[str]:
    return [
        (
            f"INCIDENT|{incident.service}|{incident.severity}|{incident.started_at}|{incident.ended_at}|"
            f"{incident.duration_minutes}|{incident.alert_count}|{incident.source_count}|"
            f"{join_or_dash(incident.sources)}|{join_or_dash(incident.alert_codes)}|"
            f"{str(incident.page).lower()}|{incident.summary}"
        )
        for incident in incidents
    ]


def build_service_digest(incidents: list[IncidentSummary], severity_rank: tuple[str, ...] | list[str]) -> list[str]:
    grouped: dict[str, list[IncidentSummary]] = {}
    for incident in incidents:
        grouped.setdefault(incident.service, []).append(incident)

    digest_rows: list[tuple[int, int, str, str]] = []
    for service, service_incidents in grouped.items():
        severity_counts: dict[str, int] = {}
        all_sources: set[str] = set()
        for incident in service_incidents:
            severity_counts[incident.severity] = severity_counts.get(incident.severity, 0) + 1
            all_sources.update(incident.sources)

        severity_bits = [
            f"{severity}:{severity_counts[severity]}"
            for severity in sorted(
                severity_counts,
                key=lambda item: severity_sort_key(item, severity_rank),
            )
        ]
        paged_count = sum(1 for incident in service_incidents if incident.page)
        digest_rows.append(
            (
                -paged_count,
                -len(service_incidents),
                service,
                (
                    f"SERVICE|{service}|{len(service_incidents)}|{paged_count}|"
                    f"{join_or_dash(severity_bits)}|{join_or_dash(sorted(all_sources))}"
                ),
            )
        )

    return [row for _, _, _, row in sorted(digest_rows)]
