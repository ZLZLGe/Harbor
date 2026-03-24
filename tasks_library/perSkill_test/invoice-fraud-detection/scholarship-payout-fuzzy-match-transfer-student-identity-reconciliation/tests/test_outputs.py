import csv
import os


EXPECTED_COLUMNS = [
    "payment_id",
    "scholarship_code",
    "beneficiary_name",
    "matched_student_id",
    "matched_student_name",
    "destination_account",
    "paid_amount",
    "reason",
]

EXPECTED_ROWS = [
    {
        "payment_id": "PAY-7002",
        "scholarship_code": "STEM-2026",
        "beneficiary_name": "Andre Walker",
        "matched_student_id": "STU-1002",
        "matched_student_name": "Andre Walker",
        "destination_account": "US83CAMP9999",
        "paid_amount": "3000.00",
        "reason": "Account Mismatch",
    },
    {
        "payment_id": "PAY-7003",
        "scholarship_code": "GLOBAL-2026",
        "beneficiary_name": "Priya Ramen",
        "matched_student_id": "STU-1003",
        "matched_student_name": "Priya Raman",
        "destination_account": "US83CAMP4403",
        "paid_amount": "1800.00",
        "reason": "Amount Mismatch",
    },
    {
        "payment_id": "PAY-7007",
        "scholarship_code": "LEAD-2026",
        "beneficiary_name": "Jamie Kim",
        "matched_student_id": "",
        "matched_student_name": "",
        "destination_account": "US83CAMP4407",
        "paid_amount": "1800.00",
        "reason": "Unmatched Student",
    },
    {
        "payment_id": "PAY-7009",
        "scholarship_code": "RESEARCH-2026",
        "beneficiary_name": "Alicia Chen",
        "matched_student_id": "STU-1009",
        "matched_student_name": "Alicia Chen",
        "destination_account": "US83CAMP0000",
        "paid_amount": "2200.00",
        "reason": "Account Mismatch",
    },
]


def read_rows():
    with open("/root/scholarship_exceptions.csv", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/scholarship_exceptions.csv")

    def test_exact_rows(self):
        fieldnames, rows = read_rows()
        assert fieldnames == EXPECTED_COLUMNS
        assert rows == EXPECTED_ROWS

    def test_clean_payments_not_flagged(self):
        _, rows = read_rows()
        flagged = {row["payment_id"] for row in rows}
        clean = {"PAY-7001", "PAY-7004", "PAY-7005", "PAY-7006", "PAY-7008", "PAY-7010"}
        assert flagged.isdisjoint(clean)

    def test_unmatched_row_has_blank_match_fields(self):
        _, rows = read_rows()
        unmatched = [row for row in rows if row["reason"] == "Unmatched Student"]
        assert unmatched == [
            {
                "payment_id": "PAY-7007",
                "scholarship_code": "LEAD-2026",
                "beneficiary_name": "Jamie Kim",
                "matched_student_id": "",
                "matched_student_name": "",
                "destination_account": "US83CAMP4407",
                "paid_amount": "1800.00",
                "reason": "Unmatched Student",
            }
        ]
