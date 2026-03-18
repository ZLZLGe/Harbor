import json
from pathlib import Path

import pytest
from pypdf import PdfReader

OUTPUT_PDF = Path("/root/completed_benefits_enrollment.pdf")
INPUT_PDF = Path("/root/benefits_enrollment_packet.pdf")
PROFILE_JSON = Path("/root/employee_profile.json")


def load_fields(path: Path):
    reader = PdfReader(str(path))
    fields = reader.get_fields()
    return reader, fields or {}


def raw_field_value(field):
    if hasattr(field, "value") and field.value is not None:
        return field.value
    return field.get("/V")


def normalized_value(field):
    value = raw_field_value(field)
    if value is None:
        return ""
    return str(value).lstrip("/")


def checkbox_checked(field):
    return normalized_value(field) not in {"", "Off"}


def expected_values():
    profile = json.loads(PROFILE_JSON.read_text())
    employee = profile["employee"]
    address = employee["address"]
    elections = profile["elections"]
    dependents = profile["dependents"]
    signature = profile["signature"]

    values = {
        "worker_full": f'{employee["first_name"]} {employee["last_name"]}',
        "worker_id": employee["employee_id"],
        "org_unit": employee["department"],
        "mail_box": employee["email"],
        "call_back": employee["phone"],
        "street_box": f'{address["street"]}, {address["city"]}, {address["state"]} {address["zip"]}',
        "hire_box": employee["hire_date"],
        "med_plan": {
            "Bronze HSA": "bronze",
            "PPO Plus": "ppo",
            "EPO Saver": "epo",
        }[elections["medical_plan"]],
        "coverage_level": {
            "Employee Only": "employee_only",
            "Employee + Spouse": "employee_spouse",
            "Family": "family",
        }[elections["coverage_tier"]],
        "dental_level": {
            "Basic Dental": "basic",
            "Enhanced Dental": "enhanced",
            "Waive Dental": "waive",
        }[elections["dental_plan"]],
        "vision_opt_in": elections["vision_enrolled"],
        "tobacco_state": "yes" if elections["tobacco_user"] else "no",
        "fsa_health": str(elections["fsa"]["healthcare"]),
        "fsa_family": str(elections["fsa"]["dependent_care"]),
        "sign_name": signature["name"],
        "sign_date": signature["date"],
    }

    dependent_fields = [
        ("dep_a_name", "dep_a_relation", "dep_a_dob"),
        ("dep_b_name", "dep_b_relation", "dep_b_dob"),
    ]
    for index, field_group in enumerate(dependent_fields):
        dependent = dependents[index] if index < len(dependents) else None
        expected = (
            dependent["name"] if dependent else "",
            dependent["relationship"] if dependent else "",
            dependent["date_of_birth"] if dependent else "",
        )
        for field_name, value in zip(field_group, expected):
            values[field_name] = value
    return values


class TestCompletedPdf:
    def test_output_exists(self):
        assert OUTPUT_PDF.exists(), f"Missing completed PDF: {OUTPUT_PDF}"

    def test_output_is_readable_pdf(self):
        reader = PdfReader(str(OUTPUT_PDF))
        assert len(reader.pages) == 2

    def test_output_preserves_form_fields(self):
        _, fields = load_fields(OUTPUT_PDF)
        required_fields = {
            "worker_full",
            "worker_id",
            "org_unit",
            "mail_box",
            "call_back",
            "street_box",
            "hire_box",
            "med_plan",
            "coverage_level",
            "dental_level",
            "vision_opt_in",
            "tobacco_state",
            "fsa_health",
            "fsa_family",
            "dep_a_name",
            "dep_a_relation",
            "dep_a_dob",
            "dep_b_name",
            "dep_b_relation",
            "dep_b_dob",
            "sign_name",
            "sign_date",
        }
        assert required_fields.issubset(fields.keys())


class TestFieldValues:
    @pytest.fixture(scope="class")
    def output_fields(self):
        _, fields = load_fields(OUTPUT_PDF)
        return fields

    def test_text_fields(self, output_fields):
        expected = expected_values()
        text_fields = [
            "worker_full",
            "worker_id",
            "org_unit",
            "mail_box",
            "call_back",
            "street_box",
            "hire_box",
            "fsa_health",
            "fsa_family",
            "dep_a_name",
            "dep_a_relation",
            "dep_a_dob",
            "dep_b_name",
            "dep_b_relation",
            "dep_b_dob",
            "sign_name",
            "sign_date",
        ]
        for field_name in text_fields:
            assert normalized_value(output_fields[field_name]) == expected[field_name]

    def test_radio_groups(self, output_fields):
        expected = expected_values()
        for field_name in ["med_plan", "coverage_level", "dental_level", "tobacco_state"]:
            assert normalized_value(output_fields[field_name]) == expected[field_name]

    def test_checkbox(self, output_fields):
        expected = expected_values()
        assert checkbox_checked(output_fields["vision_opt_in"]) is expected["vision_opt_in"]


class TestTemplateIntegrity:
    def test_blank_template_exists(self):
        assert INPUT_PDF.exists(), f"Missing input packet: {INPUT_PDF}"

    def test_template_page_count_matches_output(self):
        input_reader = PdfReader(str(INPUT_PDF))
        output_reader = PdfReader(str(OUTPUT_PDF))
        assert len(input_reader.pages) == len(output_reader.pages) == 2
