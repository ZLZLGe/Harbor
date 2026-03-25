#!/bin/bash
set -euo pipefail

TARGET_DIR="${TARGET_DIR:-/root/workspace}"
mkdir -p "${TARGET_DIR}"

cat > "${TARGET_DIR}/catalog_inventory_solution.py" <<'PYTHON_EOF'
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET


def _format_price(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def build_summary(input_path: str | Path) -> dict[str, object]:
    categories: dict[str, dict[str, object]] = {}
    total_sku_count = 0
    root = None
    currency = None

    for event, elem in ET.iterparse(input_path, events=("start", "end")):
        if event == "start" and root is None:
            root = elem
            currency = root.attrib["currency"]
            continue

        if event != "end" or elem.tag != "product":
            continue

        category = elem.find("category")
        inventory = elem.find("inventory")
        pricing = elem.find("pricing")

        category_id = category.attrib["id"]
        category_name = category.attrib["name"]
        quantity = int(inventory.attrib["quantity"])
        price = Decimal(pricing.attrib["current"])

        row = categories.get(category_id)
        if row is None:
            row = {
                "category_id": category_id,
                "category_name": category_name,
                "sku_count": 0,
                "inventory_total": 0,
                "price_min": price,
                "price_max": price,
            }
            categories[category_id] = row

        row["sku_count"] += 1
        row["inventory_total"] += quantity
        if price < row["price_min"]:
            row["price_min"] = price
        if price > row["price_max"]:
            row["price_max"] = price

        total_sku_count += 1
        if root is not None:
            root.remove(elem)
        elem.clear()

    return {
        "catalog": {
            "currency": currency,
            "category_count": len(categories),
            "total_sku_count": total_sku_count,
        },
        "categories": [
            {
                "category_id": category_id,
                "category_name": row["category_name"],
                "sku_count": row["sku_count"],
                "inventory_total": row["inventory_total"],
                "price_min": _format_price(row["price_min"]),
                "price_max": _format_price(row["price_max"]),
            }
            for category_id, row in sorted(categories.items())
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = build_summary(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
PYTHON_EOF

chmod +x "${TARGET_DIR}/catalog_inventory_solution.py"
