import json
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


INPUT_PATH = Path("/root/claim_packet.pdf")
OUTPUT_PATH = Path("/root/completed_claim_packet.pdf")
CASE_PATH = Path("/root/claim_case.json")


def load_fields(path: Path):
    reader = PdfReader(str(path))
    fields = reader.get_fields()
    assert fields is not None, f"{path} should expose fillable fields"
    return reader, fields


def field_value(field) -> str | None:
    value = field.get("/V")
    return None if value is None else str(value)


def checkbox_checked(field) -> bool:
    value = field_value(field)
    return value not in (None, "/Off", "Off")


def choice_options(field) -> list[str]:
    raw = field.get("/Opt") or []
    options = []
    for item in raw:
        if isinstance(item, list) and len(item) == 2:
            options.append(str(item[1]))
        else:
            options.append(str(item))
    return options


def test_output_exists():
    assert OUTPUT_PATH.exists(), "missing /root/completed_claim_packet.pdf"


def test_packet_structure_is_preserved():
    input_reader, input_fields = load_fields(INPUT_PATH)
    output_reader, output_fields = load_fields(OUTPUT_PATH)

    assert len(input_reader.pages) == 2
    assert len(output_reader.pages) == len(input_reader.pages)
    assert set(output_fields.keys()) == set(input_fields.keys())

    for field_name in ("subscriber_relation", "plan_selection", "place_of_service"):
        assert choice_options(output_fields[field_name]) == choice_options(input_fields[field_name])


def test_expected_values_are_filled():
    _, fields = load_fields(OUTPUT_PATH)
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))

    expected_text = {
        "claim_id": case["encounter"]["claim_reference"],
        "patient_name": case["patient"]["full_name"],
        "member_id": case["patient"]["member_id"],
        "date_of_birth": case["patient"]["date_of_birth"],
        "subscriber_relation": case["coverage"]["subscriber_relation"],
        "plan_selection": case["coverage"]["plan_selection"],
        "service_date": case["encounter"]["date_of_service"],
        "diagnosis_code": case["encounter"]["diagnosis_icd10"],
        "procedure_code": case["encounter"]["procedure_cpt"],
        "provider_npi": case["encounter"]["provider_npi"],
        "place_of_service": case["encounter"]["setting"],
        "prior_authorization": case["authorizations"]["prior_authorization"],
    }

    for field_name, expected in expected_text.items():
        assert field_value(fields[field_name]) == expected

    charge_value = field_value(fields["total_charge"])
    assert charge_value is not None
    assert Decimal(charge_value) == Decimal(f"{case['encounter']['charge_amount']:.2f}")

    assert checkbox_checked(fields["release_records"]) is True
    assert checkbox_checked(fields["accept_assignment"]) is True
    assert checkbox_checked(fields["accident_related"]) is False
