#!/usr/bin/env python3

import os
import sys

from pypdf import PdfReader

OUTPUT_PATH = "/root/workspace/equipment_checkout_filled.pdf"
EXPECTED_TEXT_FIELDS = {
    "employee_name": "Nora Patel",
    "employee_id": "FO-318",
    "department": "Field Operations",
    "phone_extension": "x4512",
    "equipment_description": "Portable thermal camera kit",
    "asset_tag": "EQ-THERM-204",
    "serial_number": "SN-TC8841",
    "checkout_date": "2026-04-09",
    "due_date": "2026-04-16",
    "primary_use": "Transformer yard inspection",
    "approving_supervisor": "Mei Chen",
}
EXPECTED_CHECKBOXES = {
    "accessory_charger": True,
    "accessory_tripod": True,
    "accessory_case": False,
    "inspected_operational": True,
    "safety_briefing_completed": True,
}


def fail(message):
    raise AssertionError(message)


def is_checked(field):
    return field.get("/V") not in (None, "/Off")


def main():
    if not os.path.exists(OUTPUT_PATH):
        fail(f"missing output file: {OUTPUT_PATH}")

    reader = PdfReader(OUTPUT_PATH)
    if len(reader.pages) != 1:
        fail(f"expected 1 page in filled form, got {len(reader.pages)}")

    fields = reader.get_fields()
    if not fields:
        fail("filled PDF does not expose form fields")

    for field_id, expected_value in EXPECTED_TEXT_FIELDS.items():
        field = fields.get(field_id)
        if field is None:
            fail(f"missing text field: {field_id}")
        actual_value = field.get("/V")
        if actual_value != expected_value:
            fail(
                f"text field mismatch for {field_id}: expected {expected_value!r}, got {actual_value!r}"
            )

    for field_id, expected_checked in EXPECTED_CHECKBOXES.items():
        field = fields.get(field_id)
        if field is None:
            fail(f"missing checkbox field: {field_id}")
        actual_checked = is_checked(field)
        if actual_checked != expected_checked:
            fail(
                f"checkbox mismatch for {field_id}: expected {expected_checked}, got {actual_checked}"
            )

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write("1.0\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        os.makedirs("/logs/verifier", exist_ok=True)
        with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
            handle.write("0.0\n")
        print(str(exc), file=sys.stderr)
        sys.exit(1)
