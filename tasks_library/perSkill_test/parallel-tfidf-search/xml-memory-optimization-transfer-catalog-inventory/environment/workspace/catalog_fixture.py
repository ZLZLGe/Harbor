#!/usr/bin/env python3

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import random
from pathlib import Path


_BASE_CATEGORIES = [
    ("appliances", "Appliances"),
    ("books", "Books"),
    ("camp", "Camping"),
    ("decor", "Home Decor"),
    ("fitness", "Fitness"),
    ("garden", "Garden"),
    ("kitchen", "Kitchen"),
    ("music", "Music"),
    ("office", "Office"),
    ("outdoor", "Outdoor"),
    ("pets", "Pets"),
    ("studio", "Studio"),
]


def _category_for(index: int) -> tuple[str, str]:
    if index < len(_BASE_CATEGORIES):
        return _BASE_CATEGORIES[index]
    return (f"dept-{index:03d}", f"Department {index:03d}")


def _format_price(cents: int) -> str:
    value = (Decimal(cents) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{value:.2f}"


def write_catalog(path: str | Path, num_products: int, num_categories: int, seed: int = 0) -> None:
    rng = random.Random(seed)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8") as handle:
        handle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        handle.write('<catalog currency="USD" source="fixture">\n')

        for product_index in range(num_products):
            category_index = (product_index * 7 + rng.randrange(num_categories)) % num_categories
            category_id, category_name = _category_for(category_index)
            sku = f"{category_id.upper().replace('-', '')}-{product_index:07d}"
            quantity = 1 + ((product_index * 13 + seed * 5 + category_index) % 250)
            cents = 500 + ((product_index * 97 + category_index * 31 + seed * 17) % 15000)
            season_code = (product_index + seed) % 4
            price = _format_price(cents)

            handle.write(f'  <product sku="{sku}">\n')
            handle.write(f'    <category id="{category_id}" name="{category_name}" />\n')
            handle.write(f'    <inventory quantity="{quantity}" />\n')
            handle.write(f'    <pricing current="{price}" />\n')
            handle.write('    <metadata>\n')
            handle.write(f'      <vendor>vendor-{(category_index % 9) + 1}</vendor>\n')
            handle.write(f'      <season>S{season_code}</season>\n')
            handle.write('    </metadata>\n')
            handle.write('  </product>\n')

        handle.write('</catalog>\n')
