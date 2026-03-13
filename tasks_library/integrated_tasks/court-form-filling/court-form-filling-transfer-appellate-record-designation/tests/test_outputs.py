from pathlib import Path

import pytest
from pypdf import PdfReader

OUTPUT_FILE = Path("/root/app003-filled.pdf")
INPUT_FILE = Path("/root/app003-blank.pdf")


REQUIRED_TEXT_FIELDS = {
    "appellant.name": "Elena Marquez",
    "appellant.street": "1842 Willow Creek Drive",
    "appellant.city": "San Jose",
    "appellant.state": "CA",
    "appellant.zip": "95125",
    "appellant.phone": "4085550174",
    "appellant.email": "elena.marquez@example.com",
    "court.name": "Superior Court of California, County of Santa Clara",
    "court.branch": "Downtown Superior Court",
    "court.street": "191 N. First Street",
    "court.city_zip": "San Jose, CA 95113",
    "case.plaintiff": "Elena Marquez",
    "case.number": "23CV418772",
    "case.defendant": "Pacific Crest Builders, Inc.",
    "notice.date_filed": "2026-02-18",
    "clerk.doc1.title": "Complaint for Negligence and Premises Liability",
    "clerk.doc1.date": "2025-06-12",
    "clerk.doc2.title": "Motion for Summary Judgment",
    "clerk.doc2.date": "2025-11-04",
    "clerk.doc3.title": "Opposition to Motion for Summary Judgment",
    "clerk.doc3.date": "2025-11-25",
    "clerk.doc4.title": "Order Granting Summary Judgment",
    "clerk.doc4.date": "2026-01-09",
    "clerk.doc5.title": "Notice of Entry of Judgment",
    "clerk.doc5.date": "2026-01-14",
    "clerk.doc6.title": "Notice of Appeal",
    "clerk.doc6.date": "2026-02-18",
    "hearing.1.date": "2025-12-12",
    "hearing.1.description": "summary judgment",
    "hearing.1.department": "16",
    "hearing.1.reporter": "A. Kim",
    "hearing.2.date": "2026-01-09",
    "hearing.2.description": "Final ruling",
    "hearing.2.department": "16",
    "hearing.2.reporter": "A. Kim",
    "signature.name": "Elena Marquez",
    "signature.date": "2026-02-20",
}


REQUIRED_CHECKBOXES = {
    "record.clerk_transcript": "/Yes",
    "record.appendix": "/Off",
    "record.agreed_statement": "/Off",
    "record.settled_statement": "/Off",
    "reporter.transcript_requested": "/Yes",
    "reporter.no_reporter_transcript": "/Off",
    "reporter.all_proceedings": "/Off",
    "reporter.selected_proceedings": "/Yes",
    "reporter.pay_estimated_cost": "/Yes",
    "reporter.fee_waiver": "/Off",
}


EMPTY_FIELDS = [
    "appeal.case_number",
    "court.clerk_notes",
    "clerk.doc7.title",
    "clerk.doc7.date",
    "clerk.additional_notes",
    "hearing.3.date",
    "hearing.3.description",
    "hearing.3.department",
    "hearing.3.reporter",
    "reporter.notes",
    "service.name",
    "service.date",
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
        assert len(output_reader.pages) == 3
        assert OUTPUT_FILE.stat().st_size > 4000

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
