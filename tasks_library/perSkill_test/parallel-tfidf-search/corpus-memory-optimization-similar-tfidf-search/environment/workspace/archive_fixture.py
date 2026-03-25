#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path


TOPICS = {
    "harbor_engineering": {
        "headline": ["seawall", "bulkhead", "breakwater", "dock", "harbor"],
        "terms": [
            "erosion",
            "sediment",
            "dredging",
            "revetment",
            "resilience",
            "berth",
            "tide",
            "sheetpile",
            "inspection",
            "stabilization",
            "caisson",
            "shoreline",
            "revetment",
            "mooring",
            "bathymetry",
            "wave",
        ],
    },
    "tram_operations": {
        "headline": ["tram", "depot", "overhead", "signal", "switch"],
        "terms": [
            "voltage",
            "wiring",
            "dispatch",
            "maintenance",
            "pantograph",
            "substation",
            "schedule",
            "headway",
            "traction",
            "insulation",
            "breaker",
            "transformer",
            "conductor",
            "downtime",
            "operator",
            "routing",
        ],
    },
    "zoning_review": {
        "headline": ["parcel", "variance", "corridor", "setback", "permit"],
        "terms": [
            "zoning",
            "frontage",
            "permit",
            "variance",
            "parcel",
            "setback",
            "height",
            "overlay",
            "façade",
            "hearing",
            "easement",
            "density",
            "compliance",
            "lot",
            "rightofway",
            "district",
        ],
    },
    "arts_programs": {
        "headline": ["gallery", "mural", "archive", "exhibit", "studio"],
        "terms": [
            "lighting",
            "conservation",
            "visitor",
            "exhibit",
            "curator",
            "mural",
            "canvas",
            "restoration",
            "pedestal",
            "installation",
            "label",
            "education",
            "tour",
            "loan",
            "catalog",
            "acquisition",
        ],
    },
    "public_health": {
        "headline": ["clinic", "screening", "triage", "dosage", "outbreak"],
        "terms": [
            "clinic",
            "outbreak",
            "screening",
            "dosage",
            "triage",
            "laboratory",
            "patient",
            "isolation",
            "surveillance",
            "vaccine",
            "specimen",
            "therapy",
            "intake",
            "diagnostic",
            "followup",
            "provider",
        ],
    },
    "stormwater": {
        "headline": ["basin", "culvert", "outfall", "runoff", "channel"],
        "terms": [
            "stormwater",
            "basin",
            "runoff",
            "culvert",
            "monitoring",
            "forecast",
            "infiltration",
            "spillway",
            "overflow",
            "detention",
            "rainfall",
            "sensor",
            "debris",
            "channel",
            "drainage",
            "hydrology",
        ],
    },
}

SHARED_TERMS = [
    "committee",
    "memorandum",
    "review",
    "finding",
    "revision",
    "district",
    "public",
    "schedule",
    "field",
    "analysis",
    "record",
    "recommendation",
    "inspection",
    "coordination",
    "briefing",
    "draft",
]

FILLERS = [
    "observed",
    "documented",
    "revised",
    "confirmed",
    "outlined",
    "reported",
    "tracked",
    "updated",
    "prepared",
    "noted",
    "staged",
    "planned",
]


@dataclass
class ArchiveRecord:
    doc_id: int
    headline: str
    desk: str
    body: str


def _sentence(topic_name: str, rng: random.Random) -> str:
    topic = TOPICS[topic_name]
    length = rng.randint(18, 34)
    words: list[str] = []
    for idx in range(length):
        roll = rng.random()
        if roll < 0.55:
            words.append(rng.choice(topic["terms"]))
        elif roll < 0.78:
            words.append(rng.choice(SHARED_TERMS))
        elif roll < 0.9:
            words.append(rng.choice(FILLERS))
        else:
            other_topic = TOPICS[rng.choice([name for name in TOPICS if name != topic_name])]
            words.append(rng.choice(other_topic["terms"]))
        if idx % 9 == 0:
            words.append(rng.choice(topic["terms"]))
    return " ".join(words)


def make_record(doc_id: int, rng: random.Random) -> ArchiveRecord:
    topic_name = rng.choice(list(TOPICS))
    topic = TOPICS[topic_name]
    headline = f"{rng.choice(topic['headline']).title()} memo {doc_id}"
    sentence_count = rng.randint(8, 16)
    body = " ".join(_sentence(topic_name, rng) for _ in range(sentence_count))
    return ArchiveRecord(doc_id=doc_id, headline=headline, desk=topic_name, body=body)


def write_corpus(path: str | Path, num_docs: int, seed: int) -> None:
    rng = random.Random(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for doc_id in range(num_docs):
            record = make_record(doc_id, rng)
            handle.write(json.dumps(asdict(record), ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic archive fixtures.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--num-docs", type=int, required=True)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    write_corpus(args.output, args.num_docs, args.seed)


if __name__ == "__main__":
    main()
