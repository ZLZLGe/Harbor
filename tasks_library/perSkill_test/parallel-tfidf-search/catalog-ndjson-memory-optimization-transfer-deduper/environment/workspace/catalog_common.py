#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


@dataclass(slots=True)
class CanonicalCatalogRecord:
    sku: str
    display_name: str
    brand: str
    category_path: tuple[str, ...]
    price_cents: int
    currency: str
    availability: str
    attributes: tuple[tuple[str, str], ...]
    tags: tuple[str, ...]
    source_record_count: int


@dataclass(slots=True)
class CatalogBuildResult:
    records: list[CanonicalCatalogRecord]
    input_count: int
    canonical_count: int
    duplicate_count: int
    elapsed_time: float


def clean_text(value) -> str:
    if value is None:
        return ""
    return _WHITESPACE_RE.sub(" ", str(value).strip())


def normalize_sku(value) -> str:
    return clean_text(value).upper()


def normalize_category_path(parts) -> tuple[str, ...]:
    normalized = []
    for part in parts or ():
        cleaned = clean_text(part).lower()
        if cleaned:
            normalized.append(cleaned)
    return tuple(normalized)


def normalize_attr_key(value) -> str:
    cleaned = clean_text(value).lower().replace("-", " ")
    return _NON_ALNUM_RE.sub("_", cleaned).strip("_")


def normalize_attr_value(value) -> str:
    return clean_text(value).lower()


def normalize_tags(tags) -> tuple[str, ...]:
    normalized = {clean_text(tag).lower() for tag in tags or () if clean_text(tag)}
    return tuple(sorted(normalized))


def parse_updated_at(value) -> datetime:
    return datetime.fromisoformat(clean_text(value).replace("Z", "+00:00"))


def iter_catalog_rows(catalog_path):
    with Path(catalog_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def canonical_record_to_dict(record: CanonicalCatalogRecord) -> dict:
    return {
        "sku": record.sku,
        "display_name": record.display_name,
        "brand": record.brand,
        "category_path": list(record.category_path),
        "price_cents": record.price_cents,
        "currency": record.currency,
        "availability": record.availability,
        "attributes": {key: value for key, value in record.attributes},
        "tags": list(record.tags),
        "source_record_count": record.source_record_count,
    }


def write_canonical_ndjson(output_path, records) -> None:
    path = Path(output_path)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = canonical_record_to_dict(record)
            handle.write(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
            handle.write("\n")
