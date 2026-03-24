import json
import os


EXPECTED_OUTPUT = [
    {
        "claim_id": "CLM-9002",
        "submitted_clinic_name": "Sun State Cardiology Assoc.",
        "matched_registry_id": "REG-4104",
        "matched_clinic_name": "Sunstate Cardiology Associates",
        "billed_npi": "1882754499",
        "service_state": "FL",
        "settlement_account": "SETT-SUNSTATE-09",
        "reason": "NPI Mismatch",
    },
    {
        "claim_id": "CLM-9003",
        "submitted_clinic_name": "Desert Bloom Womens Health",
        "matched_registry_id": "REG-4105",
        "matched_clinic_name": "Desert Bloom Women's Health",
        "billed_npi": "1417023308",
        "service_state": "NV",
        "settlement_account": "SETT-DBLOOM-15",
        "reason": "State Mismatch",
    },
    {
        "claim_id": "CLM-9004",
        "submitted_clinic_name": "Blue Mesa Urgent Care LLC",
        "matched_registry_id": "REG-4107",
        "matched_clinic_name": "Blue Mesa Urgent Care",
        "billed_npi": "1669587420",
        "service_state": "NM",
        "settlement_account": "SETT-BMESA-00",
        "reason": "Settlement Account Mismatch",
    },
    {
        "claim_id": "CLM-9005",
        "submitted_clinic_name": "North River Pediatric Ctr",
        "matched_registry_id": None,
        "matched_clinic_name": None,
        "billed_npi": "1548392204",
        "service_state": "OR",
        "settlement_account": "SETT-NRIVER-77",
        "reason": "Unmatched Clinic",
    },
    {
        "claim_id": "CLM-9008",
        "submitted_clinic_name": "Lakeside Imaging Grp",
        "matched_registry_id": "REG-4106",
        "matched_clinic_name": "Lakeside Imaging Group",
        "billed_npi": "1992845500",
        "service_state": "IL",
        "settlement_account": "SETT-LAKEIMG-00",
        "reason": "NPI Mismatch",
    },
]


def load_output():
    with open("/root/provider_claim_blocks.json", encoding="utf-8") as handle:
        return json.load(handle)


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/provider_claim_blocks.json")

    def test_exact_flagged_claims(self):
        actual = load_output()
        assert actual == EXPECTED_OUTPUT

    def test_clean_claims_not_flagged(self):
        actual = load_output()
        flagged_ids = {row["claim_id"] for row in actual}
        clean_ids = {"CLM-9001", "CLM-9006", "CLM-9007", "CLM-9009", "CLM-9010"}
        assert flagged_ids.isdisjoint(clean_ids)

    def test_unmatched_claim_has_null_match_fields(self):
        actual = load_output()
        unmatched = [row for row in actual if row["reason"] == "Unmatched Clinic"]
        assert unmatched == [
            {
                "claim_id": "CLM-9005",
                "submitted_clinic_name": "North River Pediatric Ctr",
                "matched_registry_id": None,
                "matched_clinic_name": None,
                "billed_npi": "1548392204",
                "service_state": "OR",
                "settlement_account": "SETT-NRIVER-77",
                "reason": "Unmatched Clinic",
            }
        ]

    def test_reason_precedence_keeps_npi_before_account(self):
        actual = load_output()
        lakeside = next(row for row in actual if row["claim_id"] == "CLM-9008")
        assert lakeside["reason"] == "NPI Mismatch"
