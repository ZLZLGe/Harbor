from pathlib import Path
import tomllib

from pypdf import PdfReader


OUTPUT_FILE = Path("/root/field-trip-consent-filled.pdf")
INPUT_FILE = Path("/root/field-trip-consent-form.pdf")
PACKET_FILE = Path("/root/student-registration.toml")


TEXT_FIELD_BUILDERS = {
    "student_name": lambda packet: packet["student"]["name"],
    "student_id": lambda packet: packet["student"]["student_id"],
    "grade": lambda packet: packet["student"]["grade"],
    "homeroom": lambda packet: packet["student"]["homeroom"],
    "birth_date": lambda packet: packet["student"]["birth_date"],
    "trip_name": lambda packet: packet["trip"]["name"],
    "destination": lambda packet: packet["trip"]["destination"],
    "trip_date": lambda packet: packet["trip"]["trip_date"],
    "departure_time": lambda packet: packet["trip"]["departure_time"],
    "return_time": lambda packet: packet["trip"]["return_time"],
    "transportation": lambda packet: packet["trip"]["transportation"],
    "guardian_name": lambda packet: packet["guardian"]["name"],
    "guardian_relationship": lambda packet: packet["guardian"]["relationship"],
    "guardian_phone": lambda packet: packet["guardian"]["phone"],
    "guardian_email": lambda packet: packet["guardian"]["email"],
    "emergency_name": lambda packet: packet["emergency_contact"]["name"],
    "emergency_relationship": lambda packet: packet["emergency_contact"]["relationship"],
    "emergency_phone_day": lambda packet: packet["emergency_contact"]["phone_day"],
    "emergency_phone_evening": lambda packet: packet["emergency_contact"]["phone_evening"],
    "allergies": lambda packet: packet["health"]["allergies"],
    "medications": lambda packet: packet["health"]["medications"],
    "physician_name": lambda packet: packet["health"]["physician_name"],
    "physician_phone": lambda packet: packet["health"]["physician_phone"],
    "pickup_name": lambda packet: packet["pickup"]["authorized_adult"],
    "pickup_phone": lambda packet: packet["pickup"]["authorized_phone"],
    "signature_name": lambda packet: packet["signature"]["signer_name"],
    "signature_date": lambda packet: packet["signature"]["signed_on"],
}

AUTHORIZATION_GROUPS = {
    "medical_consent": lambda packet: packet["authorization"]["has_medical_consent"],
    "otc_meds": lambda packet: packet["authorization"]["allows_otc_medication"],
    "photo_release": lambda packet: packet["authorization"]["photo_release"],
    "self_carry_epipen": lambda packet: packet["authorization"]["self_carry_epipen"],
}

BLANK_FIELDS = {
    "school_receipt_date",
    "nurse_reviewed_by",
    "volunteer_chaperone",
    "teacher_notes",
}


def load_packet():
    with open(PACKET_FILE, "rb") as handle:
        return tomllib.load(handle)


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
    assert PACKET_FILE.exists(), f"Missing input packet: {PACKET_FILE}"

    assert OUTPUT_FILE.read_bytes().startswith(b"%PDF-")
    assert OUTPUT_FILE.stat().st_size > 1000
    assert OUTPUT_FILE.read_bytes() != INPUT_FILE.read_bytes(), "Output PDF should differ from the blank form"


def test_text_fields_follow_registration_packet():
    packet = load_packet()
    fields = extract_field_values(OUTPUT_FILE)

    for field_name, builder in TEXT_FIELD_BUILDERS.items():
        expected_value = normalize_value(builder(packet))
        actual_value = normalize_value(fields.get(field_name, ""))
        assert actual_value == expected_value, f"{field_name} expected {expected_value!r}, got {actual_value!r}"


def test_authorization_yes_no_pairs_are_exclusive_and_correct():
    packet = load_packet()
    fields = extract_field_values(OUTPUT_FILE)
    selected_count = 0

    for prefix, builder in AUTHORIZATION_GROUPS.items():
        expected_yes = bool(builder(packet))
        yes_field = f"{prefix}_yes"
        no_field = f"{prefix}_no"
        yes_checked = is_checked(fields.get(yes_field, ""))
        no_checked = is_checked(fields.get(no_field, ""))

        assert yes_checked != no_checked, f"{prefix} should have exactly one option checked"
        assert yes_checked is expected_yes, f"{yes_field} state does not match packet"
        assert no_checked is (not expected_yes), f"{no_field} state does not match packet"
        selected_count += int(yes_checked) + int(no_checked)

    assert selected_count == len(AUTHORIZATION_GROUPS)


def test_school_use_only_fields_stay_blank():
    fields = extract_field_values(OUTPUT_FILE)

    for field_name in BLANK_FIELDS:
        actual_value = normalize_value(fields.get(field_name, ""))
        assert actual_value == "", f"{field_name} should be blank, got {actual_value!r}"
