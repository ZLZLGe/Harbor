from pathlib import Path

from pypdf import PdfReader


OUTPUT_FILE = Path("/root/housing-mediation-filled.pdf")
INPUT_FILE = Path("/root/housing-mediation-intake.pdf")


EXPECTED_TEXT_FIELDS = {
    "applicant_name": "Marisol Vega",
    "applicant_address": "1489 Willow Bend Apt 3",
    "applicant_city": "Oakland",
    "applicant_state": "CA",
    "applicant_zip": "94607",
    "applicant_phone": "5105550182",
    "applicant_email": "marisol.vega@example.com",
    "respondent_name": "Daniel Kim",
    "respondent_phone": "5105550199",
    "rental_address": "2218 Lakeshore Blvd Unit B",
    "rental_city": "Oakland",
    "rental_state": "CA",
    "rental_zip": "94610",
    "lease_start": "2024-06-01",
    "move_out_date": "2026-02-14",
    "deposit_paid": "2400",
    "amount_already_returned": "600",
    "amount_requested": "1800",
    "dispute_start": "2026-02-14",
    "dispute_end": "2026-03-03",
    "prior_attempts": "Email 2026-02-20; certified letter 2026-02-27.",
    "availability": "Weekday evenings.",
    "requested_outcome": "Refund remaining $1800 deposit and explain deductions in writing.",
    "signature_name": "Marisol Vega",
    "signature_date": "2026-03-05",
}

EXPECTED_CHECKED_FIELDS = {
    "applicant_role_tenant",
    "respondent_role_landlord",
    "issue_security_deposit",
    "preferred_contact_email",
}

EXPECTED_EMPTY_TEXT_FIELDS = {
    "respondent_email",
    "staff_case_number",
    "staff_intake_date",
    "staff_notes",
}

EXPECTED_UNCHECKED_FIELDS = {
    "applicant_role_landlord",
    "respondent_role_tenant",
    "issue_repair_bill",
    "issue_unpaid_rent",
    "preferred_contact_phone",
    "staff_screened",
}


def normalize_value(value):
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


def extract_field_values(pdf_path: Path):
    reader = PdfReader(str(pdf_path))
    values = {}

    for name, field in (reader.get_fields() or {}).items():
        value = field.get("/V", "")
        if hasattr(value, "get_object"):
            value = value.get_object()
        values[str(name)] = str(value) if value else ""

    for page in reader.pages:
        for annot_ref in page.get("/Annots", []) or []:
            annot = annot_ref.get_object()
            name = annot.get("/T")
            if not name:
                continue
            key = str(name)
            if key in values and values[key]:
                continue
            value = annot.get("/V", "")
            if hasattr(value, "get_object"):
                value = value.get_object()
            values[key] = str(value) if value else ""

    return values


def is_checked(value: str) -> bool:
    return str(value).strip("/").lower() in {"yes", "on", "1", "true"}


def test_output_pdf_exists_and_is_modified():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"
    assert INPUT_FILE.exists(), f"Missing input file: {INPUT_FILE}"

    assert OUTPUT_FILE.read_bytes().startswith(b"%PDF-")
    assert OUTPUT_FILE.stat().st_size > 1000
    assert OUTPUT_FILE.read_bytes() != INPUT_FILE.read_bytes(), "Output PDF should differ from the blank form"


def test_expected_text_fields():
    fields = extract_field_values(OUTPUT_FILE)
    for field_name, expected_value in EXPECTED_TEXT_FIELDS.items():
        actual = normalize_value(fields.get(field_name, ""))
        assert actual == expected_value, f"{field_name} expected {expected_value!r}, got {actual!r}"


def test_expected_checked_boxes():
    fields = extract_field_values(OUTPUT_FILE)
    for field_name in EXPECTED_CHECKED_FIELDS:
        assert is_checked(fields.get(field_name, "")), f"{field_name} should be checked"


def test_empty_text_fields_stay_blank():
    fields = extract_field_values(OUTPUT_FILE)
    for field_name in EXPECTED_EMPTY_TEXT_FIELDS:
        actual = normalize_value(fields.get(field_name, ""))
        assert actual == "", f"{field_name} should be blank, got {actual!r}"


def test_unchecked_boxes_stay_unchecked():
    fields = extract_field_values(OUTPUT_FILE)
    for field_name in EXPECTED_UNCHECKED_FIELDS:
        value = fields.get(field_name, "")
        assert not is_checked(value), f"{field_name} should be unchecked, got {value!r}"
