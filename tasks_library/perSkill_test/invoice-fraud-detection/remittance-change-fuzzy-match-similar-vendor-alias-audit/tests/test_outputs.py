import json
import os


EXPECTED_ALERTS = [
    {
        "request_id": "RC-1002",
        "submitted_vendor_name": "Blue Harbor Indl Parts Co.",
        "matched_vendor_id": "V-2002",
        "matched_vendor_name": "Blue Harbor Industrial Parts Company",
        "proposed_bank_account": "US41BHIP000777",
        "proposed_tax_id": "11-2039485",
        "reason": "Bank Account Conflict",
    },
    {
        "request_id": "RC-1003",
        "submitted_vendor_name": "Crescent Office Interiors Ltd",
        "matched_vendor_id": "V-2003",
        "matched_vendor_name": "Crescent Office Interiors Limited",
        "proposed_bank_account": "US63COIL008531",
        "proposed_tax_id": "54-9021100",
        "reason": "Tax ID Conflict",
    },
    {
        "request_id": "RC-1004",
        "submitted_vendor_name": "Greenline Logisitcs Corp.",
        "matched_vendor_id": "V-2004",
        "matched_vendor_name": "Greenline Logistics Corporation",
        "proposed_bank_account": "US07GLC999944",
        "proposed_tax_id": "88-1200456",
        "reason": "Bank Account Conflict",
    },
    {
        "request_id": "RC-1008",
        "submitted_vendor_name": "Redwood Travel Services Ltd",
        "matched_vendor_id": None,
        "matched_vendor_name": None,
        "proposed_bank_account": "US00RTS111222",
        "proposed_tax_id": "20-4455667",
        "reason": "Unmatched Vendor",
    },
    {
        "request_id": "RC-1011",
        "submitted_vendor_name": "Atlas Field Services, LLC",
        "matched_vendor_id": "V-2006",
        "matched_vendor_name": "Atlas Field Services LLC",
        "proposed_bank_account": "US90AFS310099",
        "proposed_tax_id": "72-4431999",
        "reason": "Bank Account Conflict",
    },
]


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/remittance_alerts.json")

    def test_exact_alerts(self):
        with open("/root/remittance_alerts.json", encoding="utf-8") as handle:
            actual = json.load(handle)

        assert actual == EXPECTED_ALERTS

    def test_clean_requests_not_flagged(self):
        with open("/root/remittance_alerts.json", encoding="utf-8") as handle:
            actual = json.load(handle)

        flagged_ids = {item["request_id"] for item in actual}
        clean_ids = {"RC-1001", "RC-1005", "RC-1006", "RC-1007", "RC-1009", "RC-1010"}

        assert flagged_ids.isdisjoint(clean_ids)
