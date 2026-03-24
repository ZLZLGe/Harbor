#!/usr/bin/env python3
"""Deterministic transit bulletin corpus generator."""

from __future__ import annotations

import json
import random
from pathlib import Path

from archive_common import BulletinRecord

LINE_CODES = ["red", "blue", "green", "gold", "silver"]
TOPICS = {
    "signal": {
        "nouns": ["relay", "signal", "switch", "interlocking", "cabinet", "controller", "beacon"],
        "verbs": ["inspect", "reset", "stabilize", "replace", "trace", "calibrate"],
        "adjectives": ["faulty", "intermittent", "redundant", "manual", "automatic", "degraded"],
        "labels": ["signal", "control", "priority"],
    },
    "track": {
        "nouns": ["rail", "ballast", "sleeper", "drainage", "fastener", "grinder", "junction"],
        "verbs": ["grind", "tighten", "drain", "measure", "align", "reinforce"],
        "adjectives": ["worn", "saturated", "uneven", "curved", "temporary", "nightly"],
        "labels": ["track", "maintenance", "geometry"],
    },
    "power": {
        "nouns": ["substation", "breaker", "feeder", "transformer", "voltage", "battery", "charger"],
        "verbs": ["reroute", "restore", "balance", "monitor", "energize", "isolate"],
        "adjectives": ["overhead", "stable", "backup", "portable", "nominal", "delayed"],
        "labels": ["power", "electrical", "recovery"],
    },
    "weather": {
        "nouns": ["storm", "wind", "heat", "flooding", "rainfall", "gust", "visibility"],
        "verbs": ["delay", "shelter", "reopen", "dry", "monitor", "reroute"],
        "adjectives": ["coastal", "heavy", "humid", "severe", "persistent", "overnight"],
        "labels": ["weather", "operations", "alert"],
    },
    "passenger": {
        "nouns": ["platform", "crowd", "shuttle", "announcement", "queue", "elevator", "wayfinding"],
        "verbs": ["dispatch", "direct", "board", "stage", "notify", "escort"],
        "adjectives": ["temporary", "accessible", "crowded", "peak", "express", "downtown"],
        "labels": ["customer", "station", "service"],
    },
}


def _build_record(doc_id: int, rng: random.Random) -> BulletinRecord:
    topic_name = rng.choice(list(TOPICS))
    topic = TOPICS[topic_name]
    line_code = rng.choice(LINE_CODES)
    noun_a, noun_b, noun_c = rng.sample(topic["nouns"], 3)
    verb_a, verb_b = rng.sample(topic["verbs"], 2)
    adj_a, adj_b = rng.sample(topic["adjectives"], 2)
    labels = rng.sample(topic["labels"], 2)
    shift = rng.choice(["overnight", "pre-peak", "midday", "weekend", "late-night"])

    title = f"{line_code.title()} Line {noun_a} bulletin {doc_id}"
    summary = (
        f"{adj_a.title()} {noun_a} teams will {verb_a} the {noun_b} corridor during the {shift} window "
        f"while controllers monitor {noun_c} stability."
    )
    body = (
        f"Field crews will {verb_a} the {noun_a} zone, {verb_b} the {noun_b} assets, and document "
        f"{adj_b} {noun_c} readings for the {line_code} line. Riders may see {topic_name} advisories, "
        f"temporary platform guidance, and follow-up notices once the work package closes."
    )
    tags = [topic_name, *labels, line_code, shift]
    return BulletinRecord(
        doc_id=doc_id,
        line_code=line_code,
        title=title,
        summary=summary,
        body=body,
        tags=tags,
    )


def generate_bulletin_records(num_records: int, seed: int = 0) -> list[BulletinRecord]:
    rng = random.Random(seed)
    return [_build_record(doc_id, rng) for doc_id in range(num_records)]


def write_bulletin_jsonl(path: str | Path, num_records: int, seed: int = 0) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in generate_bulletin_records(num_records, seed=seed):
            handle.write(
                json.dumps(
                    {
                        "doc_id": record.doc_id,
                        "line_code": record.line_code,
                        "title": record.title,
                        "summary": record.summary,
                        "body": record.body,
                        "tags": record.tags,
                    }
                )
            )
            handle.write("\n")
    return str(target)
