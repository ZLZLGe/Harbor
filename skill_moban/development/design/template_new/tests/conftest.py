from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/output/presentation.html"))
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/root/data/briefing"))
API_ROOT = os.environ.get("API_ROOT", "http://127.0.0.1:8111")
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium")


def read_output() -> str:
    assert OUTPUT_PATH.exists(), OUTPUT_PATH
    return OUTPUT_PATH.read_text(encoding="utf-8", errors="replace")


def soup() -> BeautifulSoup:
    return BeautifulSoup(read_output(), "html.parser")


def visible_text() -> str:
    doc = soup()
    for tag in doc(["script", "style", "noscript", "template"]):
        tag.decompose()
    return re.sub(r"\s+", " ", doc.get_text(" ", strip=True)).lower()


def snapshot() -> dict[str, Any]:
    return json.loads((DATA_ROOT / "operations_snapshot.json").read_text(encoding="utf-8"))


def brand_tokens() -> dict[str, Any]:
    return json.loads((DATA_ROOT / "brand_tokens.json").read_text(encoding="utf-8"))


def complaints() -> list[dict[str, Any]]:
    rows = []
    with (DATA_ROOT / "customer_complaints.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def station_events() -> list[dict[str, str]]:
    with (DATA_ROOT / "station_events.csv").open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def api_json(path: str) -> dict[str, Any]:
    response = requests.get(f"{API_ROOT}{path}", timeout=3)
    response.raise_for_status()
    return response.json()


def expected_summary() -> dict[str, Any]:
    snap = snapshot()
    zone_trips: dict[str, int] = defaultdict(int)
    zone_availability: dict[str, list[float]] = defaultdict(list)
    for station in snap["stations"]:
        zone = station["zone"]
        zone_trips[zone] += int(station["trips"])
        zone_availability[zone].append(float(station["avg_availability_pct"]))
    zone_avg = {
        zone: round(sum(values) / len(values), 1)
        for zone, values in zone_availability.items()
    }
    target = float(snap["zone_targets"]["availability_pct"])
    shortage_rank = sorted(zone_avg, key=lambda zone: target - zone_avg[zone], reverse=True)
    theme_counts = Counter(row["theme"] for row in complaints())
    zone_complaints = Counter(row["zone"] for row in complaints())
    weather = api_json("/api/weather-impact")
    zones = api_json("/api/service-zones")
    return {
        "zone_avg": zone_avg,
        "zone_trips": dict(zone_trips),
        "shortage_rank": shortage_rank,
        "top_themes": [theme for theme, _ in theme_counts.most_common(3)],
        "zone_complaints": dict(zone_complaints),
        "weather": weather,
        "zones": zones,
    }


def contains_number_variant(text: str, value: int | float, *, percent: bool = False) -> bool:
    candidates: set[str] = set()
    if isinstance(value, int):
        candidates.add(str(value))
        candidates.add(f"{value:,}")
        if value >= 1000:
            candidates.add(f"{value / 1000:.1f}k".lower())
            candidates.add(f"{round(value / 1000):.0f}k".lower())
    else:
        candidates.add(f"{value:.1f}")
        candidates.add(f"{round(value):.0f}")
    if percent:
        candidates |= {f"{item}%" for item in list(candidates)}
    compact = text.replace(" ", "").replace("\u202f", "")
    return any(candidate.lower() in compact for candidate in candidates)
