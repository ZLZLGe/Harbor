#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path


OUTPUT_FILE = Path(os.environ.get("OUTPUT_FILE", "/root/vendor_diff_report.json"))
EXPECTED_FILE = Path(os.environ.get("EXPECTED_FILE", "/tests/expected_output.json"))


def fail(message):
    raise AssertionError(message)


def ensure_sorted_changed_items(items):
    expected_order = sorted((item["sku"], item["field"]) for item in items)
    actual_order = [(item["sku"], item["field"]) for item in items]
    if actual_order != expected_order:
        fail("changed_items must be sorted by sku, then field")


def ensure_numeric_types(items):
    for item in items:
        if item["field"] == "unit_price":
            if not isinstance(item["old_value"], (int, float)) or not isinstance(item["new_value"], (int, float)):
                fail(f"{item['sku']} unit_price values must be numeric")
        elif item["field"] == "min_order_qty":
            if not isinstance(item["old_value"], int) or not isinstance(item["new_value"], int):
                fail(f"{item['sku']} min_order_qty values must be integers")
        else:
            fail(f"Unexpected changed field: {item['field']}")


def main():
    if not OUTPUT_FILE.exists():
        fail(f"Output file not found: {OUTPUT_FILE}")
    if not EXPECTED_FILE.exists():
        fail(f"Expected file not found: {EXPECTED_FILE}")

    output = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))

    if not isinstance(output, dict):
        fail("Output JSON must be an object")
    if set(output) != {"discontinued_skus", "changed_items"}:
        fail("Output JSON must contain exactly discontinued_skus and changed_items")
    if not isinstance(output["discontinued_skus"], list):
        fail("discontinued_skus must be a list")
    if not isinstance(output["changed_items"], list):
        fail("changed_items must be a list")

    if output["discontinued_skus"] != sorted(output["discontinued_skus"]):
        fail("discontinued_skus must be sorted ascending")

    ensure_sorted_changed_items(output["changed_items"])
    ensure_numeric_types(output["changed_items"])

    if output != expected:
        fail("Output does not match expected report")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"TEST FAILURE: {error}", file=sys.stderr)
        sys.exit(1)
