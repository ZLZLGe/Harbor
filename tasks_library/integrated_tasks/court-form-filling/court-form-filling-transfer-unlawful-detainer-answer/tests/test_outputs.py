from pathlib import Path

import pytest
from pypdf import PdfReader


OUTPUT_FILE = Path("/root/ud105-filled.pdf")
INPUT_FILE = Path("/root/ud105-blank.pdf")


REQUIRED_TEXT_FIELDS = {
    "party.name": "Maya Patel",
    "party.street": "1742 Jasmine Street, Apt. 3B",
    "party.city_state_zip": "Oakland, CA 94612",
    "party.phone": "5105550187",
    "party.email": "maya.patel.renter@gmail.com",
    "court.name": "Superior Court of California, County of Alameda",
    "court.location": "Wiley W. Manuel Courthouse",
    "court.address": "661 Washington Street, Oakland, CA 94607",
    "caption.plaintiff": "Redwood Property Management, LLC",
    "caption.defendant": "Maya Patel",
    "caption.case_number": "24UD031842",
    "signature.name": "Maya Patel",
    "signature.date": "2026-02-12",
}


TEXT_SNIPPET_FIELDS = {
    "response.denial_facts": [
        "late fees",
        "parking charges",
        "$2,800",
        "partial rent",
    ],
}


REQUIRED_CHECKBOXES = {
    "response.general_denial": "/Yes",
    "defense.notice_defective": "/Yes",
    "defense.rent_accepted_after_notice": "/Yes",
    "defense.habitability": "/Yes",
    "defense.retaliation": "/Yes",
    "request.dismiss_complaint": "/Yes",
    "request.costs": "/Yes",
    "request.attorney_fees": "/Yes",
}


UNCHECKED_CHECKBOXES = {
    "defense.discrimination": "/Off",
    "defense.nuisance": "/Off",
    "defense.other": "/Off",
    "request.jury_trial": "/Off",
}


EMPTY_FIELDS = [
    "party.bar_number",
    "court.hearing_date",
    "court.department",
    "court.clerk_initials",
    "response.other_statements",
    "defense.other_text",
    "request.other_relief",
    "signature.interpreter",
]


def normalize(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def field_value(fields, name: str) -> str:
    field = fields.get(name)
    if not field:
        return ""
    return normalize(field.get("/V", ""))


@pytest.fixture(scope="module")
def output_reader():
    if not OUTPUT_FILE.exists():
        pytest.fail(f"Output file not found: {OUTPUT_FILE}")
    return PdfReader(str(OUTPUT_FILE))


@pytest.fixture(scope="module")
def input_reader():
    if not INPUT_FILE.exists():
        pytest.fail(f"Input file not found: {INPUT_FILE}")
    return PdfReader(str(INPUT_FILE))


@pytest.fixture(scope="module")
def output_fields(output_reader):
    return output_reader.get_fields() or {}


@pytest.fixture(scope="module")
def input_fields(input_reader):
    return input_reader.get_fields() or {}


class TestPDFValid:
    def test_output_exists_and_is_pdf(self, output_reader):
        assert OUTPUT_FILE.exists()
        assert len(output_reader.pages) == 4
        assert OUTPUT_FILE.stat().st_size > 4000

    def test_output_differs_from_blank(self):
        assert OUTPUT_FILE.read_bytes() != INPUT_FILE.read_bytes()


class TestRequiredFields:
    @pytest.mark.parametrize("field_name,expected", REQUIRED_TEXT_FIELDS.items())
    def test_required_text_fields(self, output_fields, field_name, expected):
        actual = field_value(output_fields, field_name)
        assert actual, f"Field {field_name} is empty"
        assert expected in actual, f"Field {field_name} expected {expected!r}, got {actual!r}"

    @pytest.mark.parametrize("field_name,snippets", TEXT_SNIPPET_FIELDS.items())
    def test_text_snippet_fields(self, output_fields, field_name, snippets):
        actual = field_value(output_fields, field_name)
        lowered = actual.lower()
        for snippet in snippets:
            assert snippet.lower() in lowered, f"Field {field_name} missing snippet {snippet!r}: {actual!r}"

    @pytest.mark.parametrize("field_name,expected", REQUIRED_CHECKBOXES.items())
    def test_required_checkbox_values(self, output_fields, field_name, expected):
        actual = field_value(output_fields, field_name)
        assert actual == expected, f"Checkbox {field_name} expected {expected!r}, got {actual!r}"


class TestUncheckedAndBlankFields:
    @pytest.mark.parametrize("field_name,expected", UNCHECKED_CHECKBOXES.items())
    def test_checkbox_left_unchecked(self, output_fields, field_name, expected):
        actual = field_value(output_fields, field_name)
        assert actual == expected, f"Checkbox {field_name} expected {expected!r}, got {actual!r}"

    @pytest.mark.parametrize("field_name", EMPTY_FIELDS)
    def test_field_left_blank(self, output_fields, field_name):
        actual = field_value(output_fields, field_name)
        assert actual in {"", "/Off"}, f"Field {field_name} should be blank, got {actual!r}"


class TestBlankFormStructure:
    def test_expected_fields_exist(self, input_fields):
        for field_name in (
            list(REQUIRED_TEXT_FIELDS)
            + list(TEXT_SNIPPET_FIELDS)
            + list(REQUIRED_CHECKBOXES)
            + list(UNCHECKED_CHECKBOXES)
            + EMPTY_FIELDS
        ):
            assert field_name in input_fields, f"Blank form missing field {field_name}"
