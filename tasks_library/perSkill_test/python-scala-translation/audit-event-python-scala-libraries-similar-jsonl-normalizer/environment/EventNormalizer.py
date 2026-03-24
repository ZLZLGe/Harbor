from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    timestamp: str
    actor: str
    action: str
    resource: str
    severity: str
    labels: list[str]
    metadata: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventSummary:
    total: int
    by_severity: dict[str, int]
    by_actor: dict[str, int]
    label_counts: dict[str, int]
    window_start: str
    window_end: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventNormalizer:
    TIMESTAMP_FORMATS = (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S %z",
        "%Y-%m-%d",
    )
    LABEL_PATTERN = re.compile(r"#([A-Za-z0-9_-]+)")
    HIGH_PATTERN = re.compile(r"(delete|drop|disable|revoke)", re.IGNORECASE)
    MEDIUM_PATTERN = re.compile(r"(write|update|patch|rotate|change)", re.IGNORECASE)

    def __init__(self, base_dir: str | Path = ".") -> None:
        self.base_dir = Path(base_dir)

    def _resolve(self, relative_path: str | Path) -> Path:
        path = Path(relative_path)
        return path if path.is_absolute() else (self.base_dir / path)

    def _read_path(self, payload: dict[str, Any], path: tuple[str, ...]) -> str | None:
        current: Any = payload
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        if isinstance(current, str) and current.strip():
            return current.strip()
        return None

    def _pick(self, payload: dict[str, Any], *paths: tuple[str, ...], default: str) -> str:
        for path in paths:
            value = self._read_path(payload, path)
            if value is not None:
                return value
        return default

    def normalize_timestamp(self, value: str) -> str:
        raw = value.strip()
        for fmt in self.TIMESTAMP_FORMATS:
            try:
                parsed = datetime.strptime(raw, fmt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                else:
                    parsed = parsed.astimezone(timezone.utc)
                return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue
        raise ValueError(f"unsupported timestamp: {value}")

    def extract_labels(self, *parts: str | None) -> list[str]:
        labels: list[str] = []
        seen: set[str] = set()
        for part in parts:
            if not part:
                continue
            for match in self.LABEL_PATTERN.finditer(part):
                label = match.group(1).lower()
                if label not in seen:
                    seen.add(label)
                    labels.append(label)
        return labels

    def _normalize_action(self, value: str) -> str:
        normalized = re.sub(r"[^A-Z0-9]+", "_", value.strip().upper()).strip("_")
        return normalized or "UNKNOWN"

    def _classify_severity(self, action: str, message: str) -> str:
        combined = f"{action} {message}"
        if self.HIGH_PATTERN.search(combined):
            return "high"
        if self.MEDIUM_PATTERN.search(combined):
            return "medium"
        return "low"

    def normalize_event(self, payload: dict[str, Any]) -> AuditEvent:
        raw_time = self._pick(payload, ("ts",), ("timestamp",), ("occurred_at",), default="1970-01-01T00:00:00Z")
        actor = self._pick(
            payload,
            ("actor", "email"),
            ("actor", "name"),
            ("user",),
            ("principal",),
            default="unknown",
        )
        action = self._normalize_action(
            self._pick(payload, ("action",), ("event",), ("type",), default="unknown")
        )
        resource = self._pick(payload, ("resource",), ("resource", "id"), ("target",), ("object",), default="unknown")
        message = self._pick(payload, ("details",), ("message",), ("note",), default="")
        event_id = self._pick(payload, ("id",), ("event_id",), default=f"{raw_time}:{actor}:{action}")
        labels = self.extract_labels(resource, message)
        severity = self._classify_severity(action, message)
        source = self._pick(payload, ("source",), default="inline")
        return AuditEvent(
            event_id=event_id,
            timestamp=self.normalize_timestamp(raw_time),
            actor=actor,
            action=action,
            resource=resource,
            severity=severity,
            labels=labels,
            metadata={"raw_time": raw_time, "source": source},
        )

    def parse_line(self, line: str) -> AuditEvent:
        return self.normalize_event(json.loads(line))

    def load_events(self, relative_path: str | Path) -> list[AuditEvent]:
        path = self._resolve(relative_path)
        with path.open("r", encoding="utf-8") as handle:
            return [self.parse_line(line) for line in handle if line.strip()]

    def summarize(self, events: Sequence[AuditEvent]) -> EventSummary:
        by_severity = {"low": 0, "medium": 0, "high": 0}
        by_actor: dict[str, int] = {}
        label_counts: dict[str, int] = {}

        for event in events:
            by_severity[event.severity] = by_severity.get(event.severity, 0) + 1
            by_actor[event.actor] = by_actor.get(event.actor, 0) + 1
            for label in event.labels:
                label_counts[label] = label_counts.get(label, 0) + 1

        ordered_actor = {key: by_actor[key] for key in sorted(by_actor)}
        ordered_labels = {key: label_counts[key] for key in sorted(label_counts)}
        timestamps = sorted(event.timestamp for event in events)
        return EventSummary(
            total=len(events),
            by_severity=by_severity,
            by_actor=ordered_actor,
            label_counts=ordered_labels,
            window_start=timestamps[0] if timestamps else "",
            window_end=timestamps[-1] if timestamps else "",
        )

    def normalize_file(self, relative_input: str | Path, relative_output: str | Path) -> EventSummary:
        events = self.load_events(relative_input)
        output_path = self._resolve(relative_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
        return self.summarize(events)

    def load_and_summarize(self, relative_path: str | Path) -> EventSummary:
        return self.summarize(self.load_events(relative_path))


def normalize_lines(lines: Iterable[str], base_dir: str | Path = ".") -> list[dict[str, Any]]:
    normalizer = EventNormalizer(base_dir)
    return [normalizer.parse_line(line).to_dict() for line in lines if line.strip()]
