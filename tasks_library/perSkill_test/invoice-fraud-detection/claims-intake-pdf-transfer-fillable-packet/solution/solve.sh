#!/bin/bash
set -euo pipefail

cd /root

python3 - <<'PY'
import json
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader, PdfWriter

INPUT_PATH = Path("/root/claim_packet.pdf")
CASE_PATH = Path("/root/claim_case.json")
OUTPUT_PATH = Path("/root/completed_claim_packet.pdf")

case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
reader = PdfReader(str(INPUT_PATH))
fields = reader.get_fields()
if not fields:
    raise RuntimeError("input form has no fillable fields")


def field_options(field_name: str) -> list[str]:
    raw = fields[field_name].get("/Opt") or []
    options: list[str] = []
    for item in raw:
        if isinstance(item, list) and len(item) == 2:
            options.append(str(item[1]))
        else:
            options.append(str(item))
    return options


def checkbox_on_value(field_name: str) -> str:
    for page in reader.pages:
        for annot_ref in page.get("/Annots", []):
            annot = annot_ref.get_object()
            if str(annot.get("/T")) != field_name:
                continue
            normal = annot.get("/AP", {}).get("/N", {})
            for key in normal.keys():
                key_str = str(key)
                if key_str != "/Off":
                    return key_str
    raise KeyError(f"checkbox export value not found for {field_name}")


def field_pages() -> dict[str, int]:
    mapping: dict[str, int] = {}
    for page_index, page in enumerate(reader.pages):
        for annot_ref in page.get("/Annots", []):
            annot = annot_ref.get_object()
            name = annot.get("/T")
            if name is not None:
                mapping[str(name)] = page_index
    return mapping


def require_allowed(field_name: str, value: str) -> str:
    allowed = field_options(field_name)
    if value not in allowed:
        raise ValueError(f"{value!r} is not a valid option for {field_name}: {allowed}")
    return value


page_for_field = field_pages()
writer = PdfWriter()
writer.clone_document_from_reader(reader)
writer.set_need_appearances_writer()

text_and_choice_values = {
    "claim_id": case["encounter"]["claim_reference"],
    "patient_name": case["patient"]["full_name"],
    "member_id": case["patient"]["member_id"],
    "date_of_birth": case["patient"]["date_of_birth"],
    "subscriber_relation": require_allowed("subscriber_relation", case["coverage"]["subscriber_relation"]),
    "plan_selection": require_allowed("plan_selection", case["coverage"]["plan_selection"]),
    "service_date": case["encounter"]["date_of_service"],
    "diagnosis_code": case["encounter"]["diagnosis_icd10"],
    "procedure_code": case["encounter"]["procedure_cpt"],
    "provider_npi": case["encounter"]["provider_npi"],
    "place_of_service": require_allowed("place_of_service", case["encounter"]["setting"]),
    "total_charge": f"{Decimal(str(case['encounter']['charge_amount'])):.2f}",
    "prior_authorization": case["authorizations"]["prior_authorization"],
}

checkbox_values = {
    "release_records": case["authorizations"]["release_medical_records"],
    "accept_assignment": case["authorizations"]["assignment_of_benefits"],
    "accident_related": case["authorizations"]["accident_related"],
}

grouped_values: dict[int, dict[str, str]] = {}
for field_name, value in text_and_choice_values.items():
    grouped_values.setdefault(page_for_field[field_name], {})[field_name] = value

for field_name, checked in checkbox_values.items():
    grouped_values.setdefault(page_for_field[field_name], {})[field_name] = checkbox_on_value(field_name) if checked else "/Off"

for page_index, values in grouped_values.items():
    writer.update_page_form_field_values(
        writer.pages[page_index],
        values,
        auto_regenerate=False,
    )

with OUTPUT_PATH.open("wb") as handle:
    writer.write(handle)
PY
