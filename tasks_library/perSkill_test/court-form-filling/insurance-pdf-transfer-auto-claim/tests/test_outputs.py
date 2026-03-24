from pathlib import Path

from pypdf import PdfReader


OUTPUT_FILE = Path("/root/auto-claim-filled.pdf")
INPUT_FILE = Path("/root/auto-claim-form.pdf")


REQUIRED_TEXT_SNIPPETS = [
    "Alicia Gomez",
    "QP-4472819",
    "4085550134",
    "agomez.driver@example.com",
    "1187 Benton St, Santa Clara, CA 95050",
    "2022",
    "Honda Civic LX",
    "8XJR214",
    "2026-02-11",
    "07:40",
    "Level 3 parking garage at 4500 Great America Pkwy, Santa Clara, CA 95054",
    "Scraped the vehicle against a concrete support pillar while turning into a narrow parking space.",
    "Passenger-side doors and rear quarter panel.",
    "1860.75",
    "2026-02-12",
]

REQUIRED_CHECKED_FIELDS = {
    "single_vehicle_incident",
    "insured_driver_responsible",
    "vehicle_drivable",
}

REQUIRED_UNCHECKED_FIELDS = {
    "vehicle_towed",
    "police_report_filed",
    "injuries_reported",
}

REQUIRED_BLANK_FIELDS = {
    "adjuster_claim_number",
    "other_driver_name",
    "witness_contact",
    "adjuster_notes",
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


def test_output_pdf_exists_and_differs_from_blank():
    assert OUTPUT_FILE.exists(), f"Missing output file: {OUTPUT_FILE}"
    assert INPUT_FILE.exists(), f"Missing input file: {INPUT_FILE}"

    assert OUTPUT_FILE.read_bytes().startswith(b"%PDF-")
    assert OUTPUT_FILE.stat().st_size > 1000
    assert OUTPUT_FILE.read_bytes() != INPUT_FILE.read_bytes(), "Output PDF should differ from the blank form"


def test_required_claim_details_present():
    fields = extract_field_values(OUTPUT_FILE)
    combined = " ".join(normalize_value(value) for value in fields.values())

    for snippet in REQUIRED_TEXT_SNIPPETS:
        assert snippet in combined, f"Missing expected claim detail: {snippet!r}"


def test_checkbox_states_match_claim_packet():
    fields = extract_field_values(OUTPUT_FILE)

    for field_name in REQUIRED_CHECKED_FIELDS:
        assert is_checked(fields.get(field_name, "")), f"{field_name} should be checked"

    for field_name in REQUIRED_UNCHECKED_FIELDS:
        assert not is_checked(fields.get(field_name, "")), f"{field_name} should be unchecked"


def test_unmentioned_fields_stay_blank():
    fields = extract_field_values(OUTPUT_FILE)

    for field_name in REQUIRED_BLANK_FIELDS:
        actual = normalize_value(fields.get(field_name, ""))
        assert actual == "", f"{field_name} should be blank, got {actual!r}"
