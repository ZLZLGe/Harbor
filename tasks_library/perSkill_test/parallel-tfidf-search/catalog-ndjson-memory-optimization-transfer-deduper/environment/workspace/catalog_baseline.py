#!/usr/bin/env python3

from __future__ import annotations

import time
from collections import defaultdict

from catalog_common import (
    CatalogBuildResult,
    CanonicalCatalogRecord,
    clean_text,
    iter_catalog_rows,
    normalize_attr_key,
    normalize_attr_value,
    normalize_category_path,
    normalize_sku,
    normalize_tags,
    parse_updated_at,
    write_canonical_ndjson,
)


def _normalize_row(raw_row: dict, line_number: int) -> dict:
    normalized_attributes = []
    for key, value in (raw_row.get("attributes") or {}).items():
        normalized_key = normalize_attr_key(key)
        normalized_value = normalize_attr_value(value)
        if normalized_key and normalized_value:
            normalized_attributes.append((normalized_key, normalized_value))
    normalized_attributes.sort()

    return {
        "sku": normalize_sku(raw_row.get("sku")),
        "display_name": clean_text(raw_row.get("title")),
        "brand": clean_text(raw_row.get("brand")),
        "category_path": normalize_category_path(raw_row.get("category_path") or ()),
        "price_cents": int(raw_row.get("price_cents") or 0),
        "currency": clean_text(raw_row.get("currency")).upper(),
        "availability": clean_text(raw_row.get("availability")).lower(),
        "attributes": normalized_attributes,
        "tags": normalize_tags(raw_row.get("tags") or ()),
        "updated_at": parse_updated_at(raw_row.get("updated_at")),
        "line_number": line_number,
        "description_copy": clean_text(raw_row.get("description")),
        "raw_row_copy": dict(raw_row),
    }


def dedupe_catalog_baseline(catalog_path):
    start = time.perf_counter()

    raw_rows = list(iter_catalog_rows(catalog_path))
    normalized_rows = [
        _normalize_row(raw_row, line_number)
        for line_number, raw_row in enumerate(raw_rows)
    ]

    groups = defaultdict(list)
    for row in normalized_rows:
        groups[row["sku"]].append(row)

    canonical_records = []
    for sku in sorted(groups):
        group = groups[sku]
        latest_row = max(group, key=lambda row: (row["updated_at"], row["line_number"]))

        latest_attributes = {}
        for row in group:
            token = (row["updated_at"], row["line_number"])
            for key, value in row["attributes"]:
                previous = latest_attributes.get(key)
                if previous is None or token >= previous[0]:
                    latest_attributes[key] = (token, value)

        display_name = min(
            (
                (-len(row["display_name"]), row["display_name"])
                for row in group
                if row["display_name"]
            ),
            default=(0, ""),
        )[1]
        brand = min((row["brand"] for row in group if row["brand"]), default="")
        category_path = min(
            (
                (-len(row["category_path"]), row["category_path"])
                for row in group
                if row["category_path"]
            ),
            default=(0, ()),
        )[1]
        tags = tuple(sorted({tag for row in group for tag in row["tags"]}))
        attributes = tuple(
            (key, latest_attributes[key][1])
            for key in sorted(latest_attributes)
        )

        canonical_records.append(
            CanonicalCatalogRecord(
                sku=sku,
                display_name=display_name,
                brand=brand,
                category_path=category_path,
                price_cents=latest_row["price_cents"],
                currency=latest_row["currency"],
                availability=latest_row["availability"],
                attributes=attributes,
                tags=tags,
                source_record_count=len(group),
            )
        )

    elapsed_time = time.perf_counter() - start
    return CatalogBuildResult(
        records=canonical_records,
        input_count=len(normalized_rows),
        canonical_count=len(canonical_records),
        duplicate_count=len(normalized_rows) - len(canonical_records),
        elapsed_time=elapsed_time,
    )


def write_canonical_catalog_baseline(catalog_path, output_path):
    result = dedupe_catalog_baseline(catalog_path)
    write_canonical_ndjson(output_path, result.records)
    return result
