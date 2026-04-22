from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".log",
    ".txt",
    ".md",
    ".http",
    ".sh",
    ".yaml",
    ".yml",
}
SKIP_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
}
FILE_KEYWORDS = (
    "incident",
    "replay",
    "trace",
    "event",
    "log",
    "request",
    "fixture",
    "sample",
    "settlement",
    "gateway",
)
TIMESTAMP_KEYS = ("timestamp", "time", "created_at", "updated_at", "occurred_at", "event_time")
STATE_KEYS = ("state", "status", "phase")
ID_KEYS = ("settlement_id", "payout_id", "ledger_id", "request_id", "trace_id", "transaction_id", "id")
TS_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ][0-9:.+-Z]{5,}\b")
HTTP_LINE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE)\s+(\S+)")
CURL_METHOD = re.compile(r"curl\b.*?(?:-X\s+|--request\s+)(GET|POST|PUT|PATCH|DELETE)", re.I)
CURL_URL = re.compile(r"https?://[^\s'\"\\]+")


@dataclass
class Event:
    source: str
    order: int
    timestamp: str | None
    actor: str | None
    action: str | None
    state: str | None
    amount: str | None
    endpoint: str | None
    identifiers: dict[str, str]
    detail: str


def default_environment_root() -> Path:
    workspace_root = Path("/app/workspace")
    gateway_root = Path("/services/settlement-gateway")
    if workspace_root.exists() or gateway_root.exists():
        return Path("/")
    return Path(__file__).resolve().parents[3]


def scan_roots(root: Path) -> list[Path]:
    preferred = [
        Path("/app/workspace"),
        Path("/services/settlement-gateway"),
        root / "workspace",
        root / "settlement-gateway",
    ]
    existing = [path for path in preferred if path.exists()]
    return existing or [root]


def iter_candidate_files(root: Path) -> Iterable[Path]:
    for scan_root in scan_roots(root):
        for path in scan_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            lowered = str(path).lower()
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if not any(keyword in lowered for keyword in FILE_KEYWORDS):
                continue
            try:
                if path.stat().st_size > 1024 * 1024:
                    continue
            except OSError:
                continue
            yield path


def normalize_timestamp(value: str | None) -> tuple[datetime | None, str | None]:
    if not value:
        return None, None
    candidate = value.strip().replace("Z", "+00:00")
    for fmt in (
        None,
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            parsed = datetime.fromisoformat(candidate) if fmt is None else datetime.strptime(candidate, fmt)
            return parsed, value
        except ValueError:
            continue
    return None, value


def collect_identifiers(mapping: dict) -> dict[str, str]:
    ids: dict[str, str] = {}
    for key, value in mapping.items():
        if key in ID_KEYS and value not in (None, ""):
            ids[key] = str(value)
        elif key.endswith("_id") and value not in (None, ""):
            ids[key] = str(value)
    return ids


def event_from_mapping(mapping: dict, source: str, order: int, detail: str) -> Event | None:
    timestamp = next((str(mapping[key]) for key in TIMESTAMP_KEYS if key in mapping and mapping[key]), None)
    state = next((str(mapping[key]) for key in STATE_KEYS if key in mapping and mapping[key]), None)
    actor = str(mapping.get("service") or mapping.get("component") or mapping.get("actor") or "") or None
    action = str(mapping.get("event") or mapping.get("action") or mapping.get("type") or "") or None
    amount = None
    for key in ("amount", "gross_amount", "net_amount", "fee", "value"):
        if key in mapping and mapping[key] not in (None, ""):
            amount = f"{key}={mapping[key]}"
            break
    endpoint = str(mapping.get("path") or mapping.get("endpoint") or mapping.get("url") or "") or None
    identifiers = collect_identifiers(mapping)

    if not any((timestamp, state, action, amount, endpoint, identifiers)):
        return None
    return Event(
        source=source,
        order=order,
        timestamp=timestamp,
        actor=actor,
        action=action,
        state=state,
        amount=amount,
        endpoint=endpoint,
        identifiers=identifiers,
        detail=detail[:180],
    )


def walk_json(value: object, source: str, start_order: int = 0) -> list[Event]:
    events: list[Event] = []
    order = start_order

    def visit(node: object) -> None:
        nonlocal order
        if isinstance(node, dict):
            detail = ", ".join(f"{key}={node[key]}" for key in list(node.keys())[:6])
            event = event_from_mapping(node, source, order, detail)
            if event:
                events.append(event)
                order += 1
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return events


def parse_json_file(path: Path) -> list[Event]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    if path.suffix.lower() == ".jsonl":
        events: list[Event] = []
        for index, line in enumerate(text.splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            events.extend(walk_json(payload, str(path), index))
        return events

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    return walk_json(payload, str(path))


def parse_text_file(path: Path) -> list[Event]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []

    events: list[Event] = []
    for index, line in enumerate(lines):
        lowered = line.lower()
        if not any(keyword in lowered for keyword in ("settle", "reconcile", "retry", "failed", "gateway", "ledger", "status", "state")):
            continue
        timestamp_match = TS_PATTERN.search(line)
        timestamp = timestamp_match.group(0) if timestamp_match else None

        http_match = HTTP_LINE.match(line.strip())
        endpoint = http_match.group(2) if http_match else None
        action = http_match.group(1) if http_match else None

        curl_method = CURL_METHOD.search(line)
        curl_url = CURL_URL.search(line)
        if curl_method:
            action = curl_method.group(1).upper()
        if curl_url:
            endpoint = curl_url.group(0)

        state = None
        state_match = re.search(r"\b(?:state|status)[=: ]+([A-Za-z0-9_-]+)\b", line, re.I)
        if state_match:
            state = state_match.group(1)

        ids = {}
        for match in re.finditer(r"\b([a-z_]+_id)[=: ]+([A-Za-z0-9._:-]+)\b", line):
            ids[match.group(1)] = match.group(2)

        amount_match = re.search(r"\b(amount|gross_amount|net_amount|fee)[=: ]+([A-Za-z0-9._:-]+)\b", line, re.I)
        amount = f"{amount_match.group(1)}={amount_match.group(2)}" if amount_match else None

        events.append(
            Event(
                source=str(path),
                order=index,
                timestamp=timestamp,
                actor=None,
                action=action,
                state=state,
                amount=amount,
                endpoint=endpoint,
                identifiers=ids,
                detail=line.strip()[:180],
            )
        )
    return events


def load_events(root: Path) -> tuple[list[Path], list[Event]]:
    files = sorted(iter_candidate_files(root))
    events: list[Event] = []
    for path in files:
        if path.suffix.lower() in {".json", ".jsonl"}:
            events.extend(parse_json_file(path))
        else:
            events.extend(parse_text_file(path))
    return files, events


def filter_events(events: list[Event], focus_id: str | None) -> list[Event]:
    if not focus_id:
        return events
    filtered = [event for event in events if focus_id in event.detail or focus_id in " ".join(event.identifiers.values())]
    return filtered or events


def sort_events(events: list[Event]) -> list[Event]:
    def sort_key(event: Event) -> tuple[int, datetime | None, str, int]:
        parsed, _ = normalize_timestamp(event.timestamp)
        return (0 if parsed else 1, parsed, event.source, event.order)

    return sorted(events, key=sort_key)


def print_report(files: list[Path], events: list[Event], root: Path, limit_events: int) -> None:
    print(f"environment_root: {root}")
    print(f"artifact_files: {len(files)}")
    for path in files[:12]:
        print(f"- file: {path.relative_to(root)}")
    if len(files) > 12:
        print(f"- ... {len(files) - 12} more files")
    print()

    ids = Counter()
    states = Counter()
    endpoints = Counter()
    for event in events:
        ids.update(event.identifiers.values())
        if event.state:
            states[event.state] += 1
        if event.endpoint:
            endpoints[event.endpoint] += 1

    if ids:
        print("candidate_identifiers:", ", ".join(value for value, _ in ids.most_common(8)))
    else:
        print("candidate_identifiers: none")

    if states:
        print("state_transitions_seen:", ", ".join(f"{state}={count}" for state, count in states.most_common(10)))
    else:
        print("state_transitions_seen: none")

    if endpoints:
        print("endpoints_seen:", ", ".join(endpoint for endpoint, _ in endpoints.most_common(8)))
    else:
        print("endpoints_seen: none")
    print()

    print("[timeline]")
    for event in events[:limit_events]:
        pieces = [event.timestamp or "no-ts", event.action or "event", event.state or "state=?"]
        if event.amount:
            pieces.append(event.amount)
        if event.endpoint:
            pieces.append(event.endpoint)
        if event.identifiers:
            pieces.append(",".join(f"{key}={value}" for key, value in sorted(event.identifiers.items())[:3]))
        print(f"- {' | '.join(pieces)}")
        print(f"  source: {event.source}")
        print(f"  detail: {event.detail}")
    if len(events) > limit_events:
        print(f"- ... {len(events) - limit_events} more events")

    print()
    if endpoints:
        print("replay_hint: use the earliest endpoint-bearing event as the first black-box reproduction step.")
    else:
        print("replay_hint: no HTTP-bearing artifact found; pivot to fixture or log-driven replay.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct a settlement incident timeline from local artifacts.")
    parser.add_argument("--root", type=Path, default=default_environment_root(), help="Environment root to scan.")
    parser.add_argument("--focus-id", help="Prefer events mentioning this identifier.")
    parser.add_argument("--limit-events", type=int, default=25, help="Max events to print.")
    args = parser.parse_args()

    files, events = load_events(args.root)
    events = sort_events(filter_events(events, args.focus_id))
    print_report(files, events, args.root, args.limit_events)


if __name__ == "__main__":
    main()
