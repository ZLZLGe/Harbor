#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, "/root/workspace")

from catalog_fixture import write_catalog


SOLUTION_PATH = Path("/root/workspace/catalog_inventory_solution.py")
BASELINE_PATH = Path("/root/workspace/catalog_inventory_baseline.py")
SAMPLE_INPUT_PATH = Path("/root/workspace/sample_catalog.xml")
MEMORY_LIMIT_MB = 160
USAGE_WRAPPER = """
import json
import resource
import subprocess
import sys

completed = subprocess.run(sys.argv[1:], capture_output=True, text=True)
print(json.dumps({
    "returncode": completed.returncode,
    "stdout": completed.stdout,
    "stderr": completed.stderr,
    "max_rss_kb": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
}))
"""
EXPECTED_SAMPLE_REPORT = {
    "catalog": {
        "currency": "USD",
        "category_count": 3,
        "total_sku_count": 5,
    },
    "categories": [
        {
            "category_id": "appliances",
            "category_name": "Appliances",
            "sku_count": 2,
            "inventory_total": 11,
            "price_min": "179.50",
            "price_max": "249.99",
        },
        {
            "category_id": "books",
            "category_name": "Books",
            "sku_count": 2,
            "inventory_total": 52,
            "price_min": "9.99",
            "price_max": "14.95",
        },
        {
            "category_id": "music",
            "category_name": "Music",
            "sku_count": 1,
            "inventory_total": 25,
            "price_min": "29.00",
            "price_max": "29.00",
        },
    ],
}


def _format_price(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def oracle_report(input_path: Path) -> dict[str, object]:
    categories: dict[str, dict[str, object]] = {}
    total_sku_count = 0
    currency = None
    root = None

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


def run_script(script_path: Path, input_path: Path, output_path: Path) -> dict[str, object]:
    subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
    )
    with output_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def run_with_usage(script_path: Path, input_path: Path, output_path: Path) -> tuple[dict[str, object], float]:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            USAGE_WRAPPER,
            sys.executable,
            str(script_path),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["returncode"] == 0, payload["stderr"]

    with output_path.open(encoding="utf-8") as handle:
        report = json.load(handle)
    return report, float(payload["max_rss_kb"]) / 1024


def assert_contract(report: dict[str, object]) -> None:
    assert set(report) == {"catalog", "categories"}

    catalog = report["catalog"]
    assert isinstance(catalog, dict)
    assert set(catalog) == {"currency", "category_count", "total_sku_count"}
    assert isinstance(catalog["currency"], str)
    assert isinstance(catalog["category_count"], int)
    assert isinstance(catalog["total_sku_count"], int)

    categories = report["categories"]
    assert isinstance(categories, list)
    sorted_ids = sorted(row["category_id"] for row in categories)
    assert [row["category_id"] for row in categories] == sorted_ids

    for row in categories:
        assert set(row) == {
            "category_id",
            "category_name",
            "sku_count",
            "inventory_total",
            "price_min",
            "price_max",
        }
        assert isinstance(row["category_id"], str)
        assert isinstance(row["category_name"], str)
        assert isinstance(row["sku_count"], int)
        assert isinstance(row["inventory_total"], int)
        assert isinstance(row["price_min"], str)
        assert isinstance(row["price_max"], str)
        assert Decimal(row["price_min"]) <= Decimal(row["price_max"])


def test_solution_file_exists():
    assert SOLUTION_PATH.exists(), "missing /root/workspace/catalog_inventory_solution.py"


def test_sample_fixture_matches_expected_report(tmp_path: Path):
    output_path = tmp_path / "sample_summary.json"
    produced = run_script(SOLUTION_PATH, SAMPLE_INPUT_PATH, output_path)

    assert produced == EXPECTED_SAMPLE_REPORT
    assert_contract(produced)


def test_matches_baseline_on_small_generated_fixture(tmp_path: Path):
    input_path = tmp_path / "small_catalog.xml"
    baseline_output = tmp_path / "baseline_summary.json"
    solution_output = tmp_path / "solution_summary.json"

    write_catalog(input_path, num_products=2400, num_categories=9, seed=13)

    expected = run_script(BASELINE_PATH, input_path, baseline_output)
    produced = run_script(SOLUTION_PATH, input_path, solution_output)
    assert produced == expected


def test_large_fixture_correctness_and_contract(tmp_path: Path):
    input_path = tmp_path / "large_catalog.xml"
    output_path = tmp_path / "large_summary.json"

    write_catalog(input_path, num_products=36000, num_categories=28, seed=29)

    produced = run_script(SOLUTION_PATH, input_path, output_path)
    expected = oracle_report(input_path)

    assert produced == expected
    assert_contract(produced)
    assert produced["catalog"]["category_count"] == len(produced["categories"])


def test_memory_budget_on_large_fixture(tmp_path: Path):
    input_path = tmp_path / "memory_catalog.xml"
    output_path = tmp_path / "memory_summary.json"

    write_catalog(input_path, num_products=120000, num_categories=48, seed=41)

    report, rss_mb = run_with_usage(SOLUTION_PATH, input_path, output_path)
    assert rss_mb <= MEMORY_LIMIT_MB, f"peak RSS {rss_mb:.1f} MB exceeds {MEMORY_LIMIT_MB} MB"
    assert_contract(report)
