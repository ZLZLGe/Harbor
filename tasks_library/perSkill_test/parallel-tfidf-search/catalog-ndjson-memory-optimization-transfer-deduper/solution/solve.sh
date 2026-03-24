#!/bin/bash
set -euo pipefail

cat <<'PYTHON_EOF' > /root/workspace/catalog_deduper_solution.py
#!/usr/bin/env python3

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

from catalog_common import (
    CatalogBuildResult,
    CanonicalCatalogRecord,
    clean_text,
    iter_catalog_rows,
    normalize_attr_key,
    normalize_attr_value,
    normalize_category_path,
    normalize_sku,
    write_canonical_ndjson,
)


@dataclass(slots=True)
class _AttributeState:
    stamp: tuple[str, int]
    value: str


@dataclass(slots=True)
class _CatalogAccumulator:
    best_title: str
    best_title_len: int
    brand: str
    category_path: tuple[str, ...]
    category_len: int
    latest_stamp: tuple[str, int]
    price_cents: int
    currency: str
    availability: str
    attributes: dict[str, _AttributeState]
    tags: set[str]
    source_record_count: int


def _intern_clean(value, *, upper=False, lower=False) -> str:
    text = clean_text(value)
    if upper:
        text = text.upper()
    elif lower:
        text = text.lower()
    return sys.intern(text)


def dedupe_catalog(catalog_path):
    start = time.perf_counter()
    accumulators = {}
    input_count = 0

    for line_number, raw_row in enumerate(iter_catalog_rows(catalog_path)):
        input_count += 1
        sku = sys.intern(normalize_sku(raw_row.get("sku")))
        title = clean_text(raw_row.get("title"))
        brand = _intern_clean(raw_row.get("brand"))
        category_path = tuple(
            sys.intern(part)
            for part in normalize_category_path(raw_row.get("category_path") or ())
        )
        stamp = (_intern_clean(raw_row.get("updated_at")), line_number)

        accumulator = accumulators.get(sku)
        if accumulator is None:
            accumulator = _CatalogAccumulator(
                best_title=title,
                best_title_len=len(title),
                brand=brand,
                category_path=category_path,
                category_len=len(category_path),
                latest_stamp=stamp,
                price_cents=int(raw_row.get("price_cents") or 0),
                currency=_intern_clean(raw_row.get("currency"), upper=True),
                availability=_intern_clean(raw_row.get("availability"), lower=True),
                attributes={},
                tags=set(),
                source_record_count=0,
            )
            accumulators[sku] = accumulator
        else:
            if title and (-len(title), title) < (-accumulator.best_title_len, accumulator.best_title):
                accumulator.best_title = title
                accumulator.best_title_len = len(title)
            if brand and (not accumulator.brand or brand < accumulator.brand):
                accumulator.brand = brand
            if category_path and (-len(category_path), category_path) < (
                -accumulator.category_len,
                accumulator.category_path,
            ):
                accumulator.category_path = category_path
                accumulator.category_len = len(category_path)
            if stamp >= accumulator.latest_stamp:
                accumulator.latest_stamp = stamp
                accumulator.price_cents = int(raw_row.get("price_cents") or 0)
                accumulator.currency = _intern_clean(raw_row.get("currency"), upper=True)
                accumulator.availability = _intern_clean(raw_row.get("availability"), lower=True)

        accumulator.source_record_count += 1

        for key, value in (raw_row.get("attributes") or {}).items():
            normalized_key = normalize_attr_key(key)
            normalized_value = normalize_attr_value(value)
            if not normalized_key or not normalized_value:
                continue
            interned_key = sys.intern(normalized_key)
            interned_value = sys.intern(normalized_value)
            previous = accumulator.attributes.get(interned_key)
            if previous is None or stamp >= previous.stamp:
                accumulator.attributes[interned_key] = _AttributeState(stamp=stamp, value=interned_value)

        for raw_tag in raw_row.get("tags") or ():
            tag = clean_text(raw_tag).lower()
            if tag:
                accumulator.tags.add(sys.intern(tag))

    records = []
    for sku in sorted(accumulators):
        accumulator = accumulators[sku]
        records.append(
            CanonicalCatalogRecord(
                sku=sku,
                display_name=accumulator.best_title,
                brand=accumulator.brand,
                category_path=accumulator.category_path,
                price_cents=accumulator.price_cents,
                currency=accumulator.currency,
                availability=accumulator.availability,
                attributes=tuple(
                    (key, accumulator.attributes[key].value)
                    for key in sorted(accumulator.attributes)
                ),
                tags=tuple(sorted(accumulator.tags)),
                source_record_count=accumulator.source_record_count,
            )
        )

    elapsed_time = time.perf_counter() - start
    return CatalogBuildResult(
        records=records,
        input_count=input_count,
        canonical_count=len(records),
        duplicate_count=input_count - len(records),
        elapsed_time=elapsed_time,
    )


def write_canonical_catalog(catalog_path, output_path):
    result = dedupe_catalog(catalog_path)
    write_canonical_ndjson(output_path, result.records)
    return result
PYTHON_EOF

chmod +x /root/workspace/catalog_deduper_solution.py
