from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DETAIL_PATTERN = re.compile(r"([a-z_]+)\s*=\s*([^;]+)", re.IGNORECASE)
TIMESTAMP_FORMATS: list[tuple[str, bool]] = [
    ("%Y-%m-%dT%H:%M:%SZ", True),
    ("%Y-%m-%d %H:%M:%SZ", True),
    ("%Y/%m/%d %H:%M:%S %z", False),
    ("%Y-%m-%d %H:%M:%S%z", False),
    ("%d-%m-%Y %H:%M:%S", True),
]
ALIASES = {
    "login": "user_login",
    "login_success": "user_login",
    "signin": "user_login",
    "sign_in": "user_login",
    "checkout_complete": "order_completed",
    "order_placed": "order_completed",
    "purchase": "order_completed",
    "password_reset": "password_reset",
    "session_timeout": "session_timeout",
}


@dataclass(frozen=True)
class NormalizedEvent:
    id: str
    occurred_at: str
    event_type: str
    actor: str
    metadata: dict[str, str]


def normalize_timestamp(raw: str) -> str:
    text = raw.strip()
    for fmt, assume_utc in TIMESTAMP_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None and assume_utc:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise ValueError(f"unsupported timestamp: {raw}")


def canonical_event_type(raw: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", raw.strip().lower()).strip("_")
    return ALIASES.get(cleaned, cleaned)


def normalize_actor(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip().lower())


def parse_metadata(details: str | None) -> dict[str, str]:
    if not details:
        return {}
    return {
        match.group(1).lower(): match.group(2).strip()
        for match in DETAIL_PATTERN.finditer(details)
    }


def load_events(input_path: Path) -> list[dict[str, Any]]:
    lines = input_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def normalize_event(raw: dict[str, Any]) -> NormalizedEvent:
    timestamp_raw = str(raw.get("occurred_at") or raw.get("timestamp"))
    event_type_raw = str(raw.get("event_name") or raw.get("kind"))
    actor_raw = str(raw.get("user") or raw.get("actor"))
    return NormalizedEvent(
        id=str(raw["event_id"]).strip(),
        occurred_at=normalize_timestamp(timestamp_raw),
        event_type=canonical_event_type(event_type_raw),
        actor=normalize_actor(actor_raw),
        metadata=parse_metadata(raw.get("details")),
    )


def build_report(input_path: Path) -> dict[str, Any]:
    normalized = sorted(
        (normalize_event(raw) for raw in load_events(input_path)),
        key=lambda event: (event.occurred_at, event.id),
    )
    by_type: dict[str, int] = {}
    for event in normalized:
        by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
    return {
        "total_events": len(normalized),
        "by_type": dict(sorted(by_type.items())),
        "actors": sorted({event.actor for event in normalized}),
        "normalized_events": [asdict(event) for event in normalized],
    }


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run(input_path: Path, output_path: Path) -> None:
    write_report(build_report(input_path), output_path)


def main() -> None:
    run(
        Path("/root/challenge/input/events.jsonl"),
        Path("/root/challenge/output/daily_report.json"),
    )


if __name__ == "__main__":
    main()
