#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

APP_ROOT = Path(os.environ.get("TASK_APP_ROOT", "/app"))
DATA_ROOT = APP_ROOT / "data"
SITE_ROOT = DATA_ROOT / "mirror" / "site"
CHECKPOINT_PATH = DATA_ROOT / "state" / "last_scan.json"
WATCHLIST_PATH = DATA_ROOT / "watchlist.yaml"


def parse_watchlist() -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    current_alias = None
    for line in WATCHLIST_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- alias:"):
            current_alias = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("url:"):
            url = stripped.split(":", 1)[1].strip()
            sources.append((current_alias or "", url))
    return sources


def checkpoint_dt() -> datetime:
    payload = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    return datetime.fromisoformat(payload["checkpoint"].replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_feed(feed_url: str) -> list[dict]:
    path = SITE_ROOT / urlparse(feed_url).path.lstrip("/")
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    atom_ns = {"a": "http://www.w3.org/2005/Atom"}
    items: list[dict] = []

    if root.tag.endswith("rss"):
        for item in root.findall("./channel/item"):
            title = unescape((item.findtext("title") or "").strip())
            link = (item.findtext("link") or "").strip()
            published = parsedate_to_datetime((item.findtext("pubDate") or "").strip()).astimezone(timezone.utc)
            items.append({"title": title, "link": link, "published": published})
        return items

    for entry in root.findall("a:entry", atom_ns):
        title = unescape((entry.findtext("a:title", default="", namespaces=atom_ns) or "").strip())
        link_elem = entry.find("a:link", atom_ns)
        href = link_elem.get("href", "") if link_elem is not None else ""
        link = urljoin(feed_url, href)
        published_text = entry.findtext("a:published", default="", namespaces=atom_ns) or entry.findtext(
            "a:updated", default="", namespaces=atom_ns
        )
        published = datetime.fromisoformat(published_text.replace("Z", "+00:00")).astimezone(timezone.utc)
        items.append({"title": title, "link": link, "published": published})
    return items


def parse_article(article_url: str) -> dict:
    path = SITE_ROOT / urlparse(article_url).path.lstrip("/")
    text = path.read_text(encoding="utf-8")

    def grab(pattern: str) -> str:
        match = re.search(pattern, text, re.I | re.S)
        return unescape(match.group(1).strip()) if match else ""

    body_parts = [unescape(part).strip() for part in re.findall(r"<p[^>]*>(.*?)</p>", text, re.I | re.S)]
    body = " ".join(part for part in body_parts if part)
    return {
        "canonical_url": grab(r'<link rel="canonical" href="([^"]+)"'),
        "description": grab(r'<meta name="description" content="([^"]+)"'),
        "published_at": grab(r'<meta property="article:published_time" content="([^"]+)"'),
        "id": grab(r'<meta name="digest-id" content="([^"]+)"'),
        "body": body,
    }


def classify(item: dict) -> tuple[str | None, str | None]:
    text = " ".join([item["title"], item["description"], item["body"]]).lower()
    out_of_scope_markers = [
        "event invitation",
        "livestream",
        "learning resource",
        "beginner",
        "getting started",
        "company update",
        "availability update",
        "availability and reliability",
        "partner-focused",
        "partner-oriented",
        "partner marketing",
        "team narrative",
        "team story",
        "feature recap",
        "feature roundup",
        "project status update",
        "project progress update",
        "performance improvement",
        "performance improvement note",
        "partner integration",
        "trip report",
    ]
    if any(marker in text for marker in out_of_scope_markers):
        return None, None

    if "release candidate" in text:
        return "release", "low"

    if any(token in text for token in ["critical remote code execution", "malicious images", "supply chain compromises"]):
        return "security", "high"

    if any(token in text for token in ["bug bounty program is being paused", "bug bounty program paused", "security process"]):
        return "security", "medium"

    if "deprecat" in text or ("removing" in text and "model picker" in text):
        if "june 1, 2026" in text or "deadline" in text or "cutover date" in text:
            return "deprecation", "high"
        return "deprecation", "medium"

    if "billing" in text or "actions minutes" in text:
        return "workflow", "high"

    if re.search(r"node\.js .*?\(lts\)", text) or "are out!" in text or "runtime releases" in text:
        return "release", "medium"

    return None, None


def why_relevant(topic: str, priority: str) -> str:
    if topic == "deprecation" and priority == "high":
        return "Dated deprecation notice that requires workflow or policy updates."
    if topic == "deprecation":
        return "Access change that affects model or feature availability."
    if topic == "workflow":
        return "Operational workflow or billing change with a dated team impact."
    if topic == "security" and priority == "high":
        return "Security event with clear operational follow-up for engineering teams."
    if topic == "security":
        return "Security-process change that matters for monitoring and response planning."
    if topic == "release" and priority == "low":
        return "Pre-release milestone worth tracking for test and upgrade planning."
    return "Release planning signal for supported runtimes and developer tooling."


def build_expected_digest() -> dict:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))["checkpoint"]
    cutoff = checkpoint_dt()
    included: list[dict] = []
    skipped: list[dict] = []
    canonical_to_index: dict[str, int] = {}

    for alias, feed_url in parse_watchlist():
        for entry in parse_feed(feed_url):
            article = parse_article(entry["link"])
            published_at = datetime.fromisoformat(article["published_at"].replace("Z", "+00:00")).astimezone(timezone.utc)
            if published_at <= cutoff:
                skipped.append(
                    {
                        "title": entry["title"],
                        "canonical_url": article["canonical_url"],
                        "sources": [alias],
                        "skip_reason": "before_checkpoint",
                        "_published_at": article["published_at"],
                    }
                )
                continue

            topic, priority = classify({"title": entry["title"], **article})
            if topic is None or priority is None:
                skipped.append(
                    {
                        "title": entry["title"],
                        "canonical_url": article["canonical_url"],
                        "sources": [alias],
                        "skip_reason": "out_of_scope",
                        "_published_at": article["published_at"],
                    }
                )
                continue

            canonical = article["canonical_url"]
            if canonical in canonical_to_index:
                included[canonical_to_index[canonical]]["sources"].append(alias)
                skipped.append(
                    {
                        "title": entry["title"],
                        "canonical_url": canonical,
                        "sources": [alias],
                        "skip_reason": "duplicate",
                        "_published_at": article["published_at"],
                    }
                )
                continue

            included.append(
                {
                    "id": article["id"],
                    "title": entry["title"],
                    "canonical_url": canonical,
                    "published_at": article["published_at"],
                    "sources": [alias],
                    "priority": priority,
                    "topic": topic,
                    "summary": article["description"],
                    "why_relevant": why_relevant(topic, priority),
                }
            )
            canonical_to_index[canonical] = len(included) - 1

    for item in included:
        item["sources"] = sorted(set(item["sources"]))

    included.sort(key=lambda row: (row["published_at"], row["canonical_url"]), reverse=True)
    skipped.sort(key=lambda row: (row["_published_at"], row["canonical_url"], row["skip_reason"]), reverse=True)
    for row in skipped:
        row.pop("_published_at", None)

    return {
        "checkpoint_used": checkpoint,
        "new_relevant_items": included,
        "skipped_items": skipped,
    }


def render_markdown(digest: dict) -> str:
    lines = ["# Developer Productivity Feed Brief", ""]
    labels = [("high", "High Priority"), ("medium", "Medium Priority"), ("low", "Low Priority")]
    for priority_key, section_title in labels:
        lines.append(f"## {section_title}")
        section_items = [item for item in digest["new_relevant_items"] if item["priority"] == priority_key]
        if not section_items:
            lines.append("- None")
            lines.append("")
            continue
        for item in section_items:
            source_list = ", ".join(item["sources"])
            date_only = item["published_at"].split("T", 1)[0]
            lines.append(f"- {date_only} | {item['title']} | sources: {source_list} | {item['summary']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
