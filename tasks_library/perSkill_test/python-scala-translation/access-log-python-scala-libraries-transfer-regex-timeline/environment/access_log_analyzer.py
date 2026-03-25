from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

LOG_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+"
    r"client=(?P<client>[A-Za-z0-9-]+)\s+"
    r"user=(?P<user>[A-Za-z0-9_-]+)\s+"
    r"method=(?P<method>[A-Z]+)\s+"
    r"path=(?P<path>\S+)\s+"
    r"status=(?P<status>\d{3})\s+"
    r"bytes=(?P<bytes>\d+)$"
)
TIMESTAMP_FORMATS = [
    "%d/%b/%Y:%H:%M:%S %z",
    "%Y-%m-%dT%H:%M:%S%z",
]
CSV_COLUMNS = [
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
    "paths",
]


@dataclass(frozen=True)
class LogEntry:
    client_id: str
    user_id: str
    occurred_at: datetime
    path: str
    status: int
    byte_count: int


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    client_id: str
    user_id: str
    session_start_utc: str
    session_end_utc: str
    duration_minutes: int
    request_count: int
    status_2xx: int
    status_4xx: int
    status_5xx: int
    total_bytes: int
    paths: str


def parse_timestamp(raw: str) -> datetime:
    text = raw.strip()
    for fmt in TIMESTAMP_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.astimezone(timezone.utc)
    raise ValueError(f"unsupported timestamp: {raw}")


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_line(raw: str) -> LogEntry:
    match = LOG_PATTERN.fullmatch(raw.strip())
    if match is None:
        raise ValueError(f"invalid log line: {raw}")
    return LogEntry(
        client_id=match.group("client"),
        user_id=match.group("user"),
        occurred_at=parse_timestamp(match.group("timestamp")),
        path=match.group("path"),
        status=int(match.group("status")),
        byte_count=int(match.group("bytes")),
    )


def load_entries(input_path: Path) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for line in input_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(parse_line(line))
    return entries


def summarize_session(client_id: str, user_id: str, session_index: int, entries: list[LogEntry]) -> SessionSummary:
    first = entries[0]
    last = entries[-1]
    return SessionSummary(
        session_id=f"{client_id}:{user_id}:s{session_index:02d}",
        client_id=client_id,
        user_id=user_id,
        session_start_utc=format_utc(first.occurred_at),
        session_end_utc=format_utc(last.occurred_at),
        duration_minutes=int((last.occurred_at - first.occurred_at).total_seconds() // 60),
        request_count=len(entries),
        status_2xx=sum(200 <= entry.status < 300 for entry in entries),
        status_4xx=sum(400 <= entry.status < 500 for entry in entries),
        status_5xx=sum(500 <= entry.status < 600 for entry in entries),
        total_bytes=sum(entry.byte_count for entry in entries),
        paths="|".join(sorted({entry.path for entry in entries})),
    )


def analyze(input_path: Path, session_gap_minutes: int) -> list[SessionSummary]:
    grouped: dict[tuple[str, str], list[LogEntry]] = {}
    for entry in load_entries(input_path):
        grouped.setdefault((entry.client_id, entry.user_id), []).append(entry)

    summaries: list[SessionSummary] = []
    for (client_id, user_id), entries in grouped.items():
        ordered = sorted(entries, key=lambda entry: (entry.occurred_at, entry.path, entry.status))
        current: list[LogEntry] = []
        session_index = 1
        for entry in ordered:
            if not current:
                current.append(entry)
                continue
            gap_minutes = int((entry.occurred_at - current[-1].occurred_at).total_seconds() // 60)
            if gap_minutes > session_gap_minutes:
                summaries.append(summarize_session(client_id, user_id, session_index, current))
                session_index += 1
                current = [entry]
            else:
                current.append(entry)
        if current:
            summaries.append(summarize_session(client_id, user_id, session_index, current))

    return sorted(summaries, key=lambda summary: (summary.session_start_utc, summary.session_id))


def write_csv(summaries: list[SessionSummary], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for summary in summaries:
            writer.writerow(asdict(summary))


def run(input_path: Path, output_path: Path, session_gap_minutes: int) -> None:
    write_csv(analyze(input_path, session_gap_minutes), output_path)


def main() -> None:
    run(
        Path("/root/challenge/input/access.log"),
        Path("/root/challenge/output/session_summary.csv"),
        30,
    )


if __name__ == "__main__":
    main()
