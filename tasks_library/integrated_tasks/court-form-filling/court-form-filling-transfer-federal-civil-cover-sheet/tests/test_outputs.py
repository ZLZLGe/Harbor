from pathlib import Path

import pytest
from pypdf import PdfReader

OUTPUT_FILE = Path("/root/js44-filled.pdf")
INPUT_FILE = Path("/root/js44-blank.pdf")


REQUIRED_TEXT_FIELDS = {
    "case.title": "Angela Ruiz v. Lakeshore Bistro Group, LLC",
    "plaintiff.name": "Angela Ruiz",
    "plaintiff.county": "Cook",
    "defendant.name": "Lakeshore Bistro Group, LLC",
    "defendant.county": "Cook",
    "cause.statute": "29 U.S.C. § 207",
    "cause.description": "Fair Labor Standards Act",
}


REQUIRED_CHECKBOXES = {
    "jurisdiction_us_plaintiff": "/Off",
    "jurisdiction_us_defendant": "/Off",
    "jurisdiction_federal_question": "/Yes",
    "jurisdiction_diversity": "/Off",
    "origin_original": "/Yes",
    "origin_removed": "/Off",
    "origin_remanded": "/Off",
    "origin_reinstated": "/Off",
    "origin_transferred": "/Off",
    "origin_multidistrict": "/Off",
    "jury_yes": "/Yes",
    "jury_no": "/Off",
    "nature_110_insurance": "/Off",
    "nature_190_other_contract": "/Off",
    "nature_310_airplane": "/Off",
    "nature_442_employment": "/Off",
    "nature_710_flsa": "/Yes",
    "nature_790_other_labor": "/Off",
    "nature_820_copyright": "/Off",
    "nature_840_trademark": "/Off",
}


EMPTY_FIELDS = [
    "court.case_number",
    "court.judge",
    "court.receipt_number",
    "complaint.demand_amount",
    "court.related_case",
    "nature.notes",
]


def normalize_field_value(value):
    if value is None:
        return ""
    return str(value).strip()


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


def field_value(fields, name: str) -> str:
    field = fields.get(name)
    if not field:
        return ""
    value = field.get("/V", "")
    return normalize_field_value(value)


class TestPDFValid:
    def test_output_exists_and_is_pdf(self, output_reader):
        assert OUTPUT_FILE.exists()
        assert len(output_reader.pages) == 2
        assert OUTPUT_FILE.stat().st_size > 3000

    def test_output_differs_from_blank(self):
        assert OUTPUT_FILE.read_bytes() != INPUT_FILE.read_bytes()


class TestRequiredFields:
    @pytest.mark.parametrize("field_name,expected", REQUIRED_TEXT_FIELDS.items())
    def test_required_text_fields(self, output_fields, field_name, expected):
        actual = field_value(output_fields, field_name)
        assert actual, f"Field {field_name} is empty"
        assert expected in actual, f"Field {field_name} expected {expected!r}, got {actual!r}"

    @pytest.mark.parametrize("field_name,expected", REQUIRED_CHECKBOXES.items())
    def test_required_checkbox_values(self, output_fields, field_name, expected):
        actual = field_value(output_fields, field_name)
        assert actual == expected, f"Checkbox {field_name} expected {expected!r}, got {actual!r}"


class TestBlankFields:
    @pytest.mark.parametrize("field_name", EMPTY_FIELDS)
    def test_field_left_blank(self, output_fields, field_name):
        actual = field_value(output_fields, field_name)
        assert actual in {"", "/Off"}, f"Field {field_name} should be blank, got {actual!r}"


class TestFormStructure:
    def test_expected_fields_exist_in_blank_form(self, input_fields):
        for field_name in list(REQUIRED_TEXT_FIELDS) + list(REQUIRED_CHECKBOXES) + EMPTY_FIELDS:
            assert field_name in input_fields, f"Blank form missing field {field_name}"
