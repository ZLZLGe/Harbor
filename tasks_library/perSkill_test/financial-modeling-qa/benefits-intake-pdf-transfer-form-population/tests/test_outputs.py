import hashlib
import os

from pypdf import PdfReader


INPUT_PDF = "/root/benefits_packet.pdf"
INPUT_JSON = "/root/employee_profile.json"
OUTPUT_PDF = "/root/completed_benefits_packet.pdf"

EXPECTED_TEMPLATE_SHA256 = "17f89e05ba710e0aa4fd04836d00ac9867d4b88608e322a00f11ecae3dc5d265"
EXPECTED_PROFILE_SHA256 = "e9fe85bd58e27b5d0978ebb398c85f3b568220e24133b0c363cc9b7fa60e8b54"


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_form_values(path: str) -> dict[str, str]:
    reader = PdfReader(path)
    values: dict[str, str] = {}
    for page in reader.pages:
        for annot_ref in page.get("/Annots", []):
            annot = annot_ref.get_object()
            field_name = annot.get("/T")
            value = annot.get("/V")
            if field_name is None:
                continue
            values[str(field_name)] = "" if value is None else str(value)
    return values


class TestOutputs:
    def test_inputs_exist_and_match_expected_assets(self):
        assert os.path.exists(INPUT_PDF), f"Missing input file: {INPUT_PDF}"
        assert os.path.exists(INPUT_JSON), f"Missing input file: {INPUT_JSON}"
        assert sha256(INPUT_PDF) == EXPECTED_TEMPLATE_SHA256
        assert sha256(INPUT_JSON) == EXPECTED_PROFILE_SHA256

    def test_output_pdf_exists(self):
        assert os.path.exists(OUTPUT_PDF), f"Missing output file: {OUTPUT_PDF}"

    def test_output_is_two_page_pdf(self):
        reader = PdfReader(OUTPUT_PDF)
        assert len(reader.pages) == 2, "The completed packet must remain a two-page PDF"

    def test_text_fields_are_filled(self):
        values = read_form_values(OUTPUT_PDF)
        assert values["employee_name"] == "Avery Chen"
        assert values["employee_id"] == "EMP-20481"
        assert values["department"] == "People Operations"
        assert values["hire_date"] == "2023-11-06"
        assert values["employee_signature"] == "Avery Chen"
        assert values["signature_date"] == "2026-03-01"
        assert values["dependent_1_name"] == "Jordan Chen"
        assert values["dependent_1_relationship"] == "Spouse"
        assert values["dependent_1_dob"] == "1990-02-21"
        assert values["dependent_2_name"] == "Mila Chen"
        assert values["dependent_2_relationship"] == "Child"
        assert values["dependent_2_dob"] == "2018-07-14"
        assert values["dependent_3_name"] == ""
        assert values["dependent_3_relationship"] == ""
        assert values["dependent_3_dob"] == ""
        assert values["hsa_contribution_per_pay_period"] == "125.00"

    def test_checkboxes_are_set_correctly(self):
        values = read_form_values(OUTPUT_PDF)
        assert values["medical_plan_ppo"] == "/Yes"
        assert values["medical_plan_hmo"] == "/Off"
        assert values["dental_enrolled"] == "/Off"
        assert values["vision_enrolled"] == "/Yes"
        assert values["tobacco_free"] == "/Yes"
        assert values["fsa_election"] == "/Off"
