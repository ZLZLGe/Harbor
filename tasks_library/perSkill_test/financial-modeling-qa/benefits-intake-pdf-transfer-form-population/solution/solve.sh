#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject, TextStringObject

INPUT_PDF = "/root/benefits_packet.pdf"
INPUT_JSON = "/root/employee_profile.json"
OUTPUT_PDF = "/root/completed_benefits_packet.pdf"


with open(INPUT_JSON, "r", encoding="utf-8") as f:
    profile = json.load(f)

employee = profile["employee"]
benefits = profile["benefits"]
signature = profile["signature"]
dependents = profile["dependents"]

field_values = {
    "employee_name": employee["name"],
    "employee_id": employee["employee_id"],
    "department": employee["department"],
    "hire_date": employee["hire_date"],
    "medical_plan_ppo": benefits["medical_plan"] == "PPO",
    "medical_plan_hmo": benefits["medical_plan"] == "HMO",
    "dental_enrolled": benefits["dental_enrolled"],
    "vision_enrolled": benefits["vision_enrolled"],
    "tobacco_free": benefits["tobacco_free"],
    "employee_signature": signature["signed_by"],
    "signature_date": signature["signed_on"],
    "fsa_election": benefits["fsa_election"],
    "hsa_contribution_per_pay_period": benefits["hsa_contribution_per_pay_period"],
}

for index in range(3):
    dep = dependents[index] if index < len(dependents) else {}
    row = index + 1
    field_values[f"dependent_{row}_name"] = dep.get("name", "")
    field_values[f"dependent_{row}_relationship"] = dep.get("relationship", "")
    field_values[f"dependent_{row}_dob"] = dep.get("date_of_birth", "")

reader = PdfReader(INPUT_PDF)
writer = PdfWriter()
writer.clone_document_from_reader(reader)

acro_form = writer._root_object.get("/AcroForm")
if acro_form is not None:
    acro_form.get_object().update({NameObject("/NeedAppearances"): BooleanObject(True)})

for page in writer.pages:
    for annot_ref in page.get("/Annots", []):
        annot = annot_ref.get_object()
        field_name = annot.get("/T")
        if field_name not in field_values:
            continue

        value = field_values[field_name]
        if annot.get("/FT") == "/Btn":
            state = NameObject("/Yes" if value else "/Off")
            annot.update({NameObject("/V"): state, NameObject("/AS"): state})
        else:
            annot.update({NameObject("/V"): TextStringObject(str(value))})

with open(OUTPUT_PDF, "wb") as f:
    writer.write(f)
PY
