#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the engineering release digest.")
    parser.add_argument("--bundle-root", default="/app/release-watch")
    parser.add_argument("--workspace-root", default="/app/workspace")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_targets(bundle_root: Path) -> list[dict[str, str]]:
    with (bundle_root / "data" / "watch_targets.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ensure_seed_db(workspace_root: Path, contract: dict[str, Any]) -> Path:
    state_db = workspace_root / contract["state_db_file"]
    if state_db.exists():
        try:
            conn = sqlite3.connect(state_db)
            try:
                tables = {
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                }
            finally:
                conn.close()
            if {"blogs", "articles"}.issubset(tables):
                return state_db
        except sqlite3.DatabaseError:
            pass
    raise FileNotFoundError("The watch database is missing; seed restore still needs to be wired.")


def current_watch_rows(state_db: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    conn = sqlite3.connect(state_db)
    conn.row_factory = sqlite3.Row
    try:
        tracked = [
            dict(row)
            for row in conn.execute("SELECT name, url, feed_url FROM blogs ORDER BY name")
        ]
        unread = [
            dict(row)
            for row in conn.execute(
                """
                SELECT b.name AS label, a.title, a.url, a.published_date
                FROM articles a
                JOIN blogs b ON b.id = a.blog_id
                WHERE a.is_read = 0
                ORDER BY a.published_date DESC, a.id ASC
                """
            )
        ]
    finally:
        conn.close()
    return tracked, unread


def replace_block(text: str, tier: str, lines: list[str]) -> str:
    start_marker = f"<!-- DIGEST-START:{tier} -->"
    end_marker = f"<!-- DIGEST-END:{tier} -->"
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker)
    return text[:start] + "\n" + "\n".join(lines) + "\n" + text[end:]


def main() -> int:
    args = parse_args()
    bundle_root = Path(args.bundle_root)
    workspace_root = Path(args.workspace_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    contract = load_json(bundle_root / "contracts" / "digest_contract.json")
    targets = load_targets(bundle_root)
    state_db = ensure_seed_db(workspace_root, contract)
    tracked_rows, unread_rows = current_watch_rows(state_db)

    draft = (bundle_root / "drafts" / contract["output_file"]).read_text(encoding="utf-8")
    grouped: dict[str, list[str]] = {"high": [], "standard": []}
    tracked_sources: list[dict[str, Any]] = []

    high_labels = {targets[0]["label"], targets[1]["label"]}
    for row in targets:
        tracked_sources.append(
            {
                "source_id": row["source_id"],
                "label": row["label"],
                "priority_tier": row["priority_tier"],
                "homepage_url": row["homepage_url"],
                "resolved_feed_reference": row["feed_override_snapshot"] or row["homepage_snapshot"],
                "content_format": "atom" if row["feed_override_snapshot"].endswith(".atom") else "rss",
                "article_count": sum(1 for item in tracked_rows if item["name"] == row["label"]),
                "unread_count": sum(1 for item in unread_rows if item["label"] == row["label"]),
                "latest_published_at": "",
            }
        )

    for unread in unread_rows:
        tier = "high" if unread["label"] in high_labels else "standard"
        grouped[tier].append(
            f"- {unread['label']} | {unread['title']} | {str(unread['published_date'])[:10]} | {unread['url']}"
        )

    for section in contract["required_sections"]:
        tier = section["tier"]
        lines = grouped[tier] or ["No new items."]
        draft = replace_block(draft, tier, lines)

    cleaned = []
    for line in draft.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in contract["cleanup_tokens"]):
            continue
        if line.startswith("<!-- DIGEST-START:") or line.startswith("<!-- DIGEST-END:"):
            continue
        cleaned.append(line.rstrip())

    (output_root / contract["output_file"]).write_text("\n".join(cleaned).strip() + "\n", encoding="utf-8")
    (output_root / contract["inventory_file"]).write_text(
        json.dumps(
            {
                "tracked_sources": tracked_sources,
                "removed_blog_names": [],
                "notes": [
                    "Starter build: the watch database has not been reconciled to the registry.",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_root / contract["manifest_file"]).write_text(
        json.dumps(
            {
                "digest_path": contract["output_file"],
                "delivered_article_urls": [item["url"] for item in unread_rows],
                "read_marked_article_urls": [],
                "tracked_source_ids": [row["source_id"] for row in targets],
                "removed_blog_names": [],
                "source_files": ["data/watch_targets.csv", contract["seed_state_file"]],
                "state_db_path": contract["state_db_file"],
                "notes": [
                    "Starter build: add/remove/scan and read-marking steps still need completion.",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
