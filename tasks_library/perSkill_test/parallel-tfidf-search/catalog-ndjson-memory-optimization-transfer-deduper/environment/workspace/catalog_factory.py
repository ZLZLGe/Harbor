#!/usr/bin/env python3

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


REPEATED_DESCRIPTION = (
    "Warehouse feed snapshot with repeated merchandising copy and sparse supplier "
    "fields. This sentence appears many times to amplify repeated strings in the "
    "naive baseline."
)

_BRANDS = [
    "Northwind",
    "Hearthline",
    "Summit Peak",
    "Bright Harbor",
    "Anchor Lane",
]

_BASE_TITLES = [
    "Commuter Tote",
    "Trail Bottle",
    "Desk Lamp",
    "Stoneware Mug",
    "Wool Throw",
    "Packing Cube",
]

_CATEGORY_PATHS = {
    "Commuter Tote": ["bags", "totes", "office"],
    "Trail Bottle": ["hydration", "bottles"],
    "Desk Lamp": ["lighting", "desk", "task lamps"],
    "Stoneware Mug": ["kitchen", "drinkware", "mugs"],
    "Wool Throw": ["home", "blankets"],
    "Packing Cube": ["travel", "organization"],
}

_ATTRIBUTE_TEMPLATES = {
    "Commuter Tote": {
        "Color": ["Slate", "Black", "Clay"],
        "Material": ["Recycled Nylon"],
        "Laptop Sleeve": ["Yes"],
    },
    "Trail Bottle": {
        "Color": ["Glacier", "Fern"],
        "Capacity ML": ["500", "750"],
        "Insulated": ["Yes"],
    },
    "Desk Lamp": {
        "Finish": ["Matte Black", "Brushed Brass"],
        "Bulb Included": ["No", "Yes"],
    },
    "Stoneware Mug": {
        "Color": ["Sand", "Moss"],
        "Microwave Safe": ["Yes"],
        "Volume ML": ["350", "400"],
    },
    "Wool Throw": {
        "Color": ["Oatmeal", "Pebble"],
        "Material": ["Wool Blend"],
        "Machine Washable": ["No"],
    },
    "Packing Cube": {
        "Color": ["Graphite", "Sage"],
        "Set Size": ["3", "5"],
        "Compression": ["Yes"],
    },
}

_TAG_TEMPLATES = {
    "Commuter Tote": ["commute", "office", "travel"],
    "Trail Bottle": ["trail", "hydration", "gift"],
    "Desk Lamp": ["workspace", "lighting", "gift"],
    "Stoneware Mug": ["kitchen", "gift", "home"],
    "Wool Throw": ["home", "gift", "winter"],
    "Packing Cube": ["travel", "organize", "luggage"],
}


def write_catalog_ndjson(path, num_products=120, duplicates_per_product=6, seed=7):
    rng = random.Random(seed)
    output_path = Path(path)
    start = datetime(2025, 1, 1, 8, 0, 0)
    row_count = 0

    with output_path.open("w", encoding="utf-8") as handle:
        for product_index in range(num_products):
            base_title = _BASE_TITLES[product_index % len(_BASE_TITLES)]
            brand = _BRANDS[product_index % len(_BRANDS)]
            category_path = _CATEGORY_PATHS[base_title]
            attribute_template = _ATTRIBUTE_TEMPLATES[base_title]
            tag_template = _TAG_TEMPLATES[base_title]
            sku_prefix = "".join(part[0] for part in base_title.split())[:3]
            sku = f"{sku_prefix}-{product_index:05d}"

            for duplicate_index in range(duplicates_per_product):
                title = base_title
                if duplicate_index % 3 == 1:
                    if base_title == "Commuter Tote":
                        title = f"{base_title} {18 + (product_index % 4)}L"
                    else:
                        title = f"{base_title} Large"
                if duplicate_index % 4 == 0:
                    title = f"  {title}  "

                attributes = {}
                for key, choices in attribute_template.items():
                    include_value = rng.random() < 0.72 or duplicate_index == duplicates_per_product - 1
                    if not include_value:
                        continue
                    value = choices[(product_index + duplicate_index) % len(choices)]
                    if duplicate_index % 5 == 0:
                        value = f" {value} "
                    attributes[key] = value

                tags = [
                    tag_template[(duplicate_index + offset) % len(tag_template)]
                    for offset in range(2)
                ]
                if duplicate_index % 2 == 0:
                    tags.append(tag_template[0].upper())

                record = {
                    "sku": sku.lower() if duplicate_index % 2 else sku,
                    "title": title,
                    "brand": f" {brand} " if duplicate_index % 3 == 0 else brand,
                    "category_path": category_path[: 2 + (duplicate_index % max(1, len(category_path) - 1))],
                    "price_cents": 1500 + (product_index % 120) * 125 + duplicate_index * 5,
                    "currency": " usd " if duplicate_index % 2 == 0 else "USD",
                    "availability": ["in_stock", "limited", "preorder"][duplicate_index % 3],
                    "attributes": attributes,
                    "tags": tags,
                    "description": f"{REPEATED_DESCRIPTION} Product family {base_title}.",
                    "updated_at": (start + timedelta(minutes=product_index * 3 + duplicate_index)).isoformat() + "Z",
                }
                handle.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False))
                handle.write("\n")
                row_count += 1

    return row_count
