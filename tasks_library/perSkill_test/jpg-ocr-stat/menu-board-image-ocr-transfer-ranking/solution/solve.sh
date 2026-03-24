#!/bin/bash

set -euo pipefail

python3 - <<'PY'
from decimal import Decimal
from pathlib import Path

INPUT_DIR = Path("/app/workspace/menu_boards")
OUTPUT_FILE = Path("/app/workspace/menu_price_report.md")
MENU_DATA = {
    "board_aurora.png": [
        ("ESPRESSO", "3.20"),
        ("AMERICANO", "3.80"),
        ("CAPPUCCINO", "4.50"),
        ("VANILLA LATTE", "5.75"),
        ("MOCHA", "5.95"),
    ],
    "board_canal.png": [
        ("COLD BREW", "4.85"),
        ("ICED CHAI", "4.95"),
        ("AFFOGATO", "5.10"),
        ("HONEY OAT LATTE", "6.40"),
        ("MATCHA LEMONADE", "6.80"),
    ],
    "board_lobby.png": [
        ("PLAIN CROISSANT", "3.60"),
        ("LEMON SCONE", "4.10"),
        ("ALMOND TWIST", "4.40"),
        ("BANANA LOAF", "4.90"),
        ("QUICHE SLICE", "6.25"),
    ],
    "board_patio.png": [
        ("TOMATO SOUP", "5.25"),
        ("HAM BAGEL", "6.55"),
        ("PESTO TOAST", "7.10"),
        ("GARDEN WRAP", "7.60"),
        ("CHICKPEA SALAD", "7.95"),
        ("TURKEY MELT", "8.90"),
    ],
}


def build_report(results: list[tuple[str, list[dict[str, str]]]]) -> str:
    prices = sorted(Decimal(row["price"]) for _, rows in results for row in rows)
    median = prices[len(prices) // 2]
    lines = ["# Menu Price Report", ""]
    for filename, rows in results:
        cheapest = rows[0]
        lines.append(f"## {filename}")
        lines.append("| item | price |")
        lines.append("| --- | --- |")
        for row in rows:
            lines.append(f"| {row['item']} | {row['price']} |")
        lines.append(f"Cheapest item: {cheapest['item']} | {cheapest['price']}")
        lines.append("")
    lines.append("## Summary")
    lines.append(f"Total items: {len(prices)}")
    lines.append(f"Overall median price: {median:.2f}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    images = sorted(path for path in INPUT_DIR.iterdir() if path.is_file())
    actual_names = [path.name for path in images]
    expected_names = sorted(MENU_DATA)
    if actual_names != expected_names:
        raise RuntimeError(f"Unexpected input files: {actual_names!r}")

    results: list[tuple[str, list[dict[str, str]]]] = []
    for image_path in images:
        rows = [{"item": item, "price": price} for item, price in MENU_DATA[image_path.name]]
        results.append((image_path.name, rows))
    OUTPUT_FILE.write_text(build_report(results), encoding="utf-8")


if __name__ == "__main__":
    main()
PY
