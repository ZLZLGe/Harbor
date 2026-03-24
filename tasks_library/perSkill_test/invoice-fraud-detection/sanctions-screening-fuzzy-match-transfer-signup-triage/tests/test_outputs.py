import csv
import os
import sys


OUTPUT_PATH = "/root/watchlist_hits.tsv"
EXPECTED_HEADER = [
    "signup_id",
    "submitted_name",
    "date_of_birth",
    "country_code",
    "matched_entity_id",
    "matched_name",
    "match_basis",
    "program",
]
EXPECTED_ROWS = [
    {
        "signup_id": "SU-001",
        "submitted_name": "Alexandr Petrof",
        "date_of_birth": "1981-04-11",
        "country_code": "CY",
        "matched_entity_id": "WL-1001",
        "matched_name": "Aleksandr Petrov",
        "match_basis": "DOB+Country",
        "program": "EU Asset Freeze",
    },
    {
        "signup_id": "SU-002",
        "submitted_name": "Muhamad Al Hakim",
        "date_of_birth": "1977-09-03",
        "country_code": "DE",
        "matched_entity_id": "WL-1002",
        "matched_name": "Mohammad Al-Hakim",
        "match_basis": "DOB",
        "program": "OFAC SDN",
    },
    {
        "signup_id": "SU-003",
        "submitted_name": "Wei Li",
        "date_of_birth": "1988-01-19",
        "country_code": "US",
        "matched_entity_id": "WL-1003",
        "matched_name": "Li Wei",
        "match_basis": "DOB",
        "program": "UN 1718",
    },
    {
        "signup_id": "SU-004",
        "submitted_name": "Natalya Orlova",
        "date_of_birth": "1992-02-02",
        "country_code": "BY",
        "matched_entity_id": "WL-1004",
        "matched_name": "Natalia Orlova",
        "match_basis": "Country",
        "program": "UK Sanctions List",
    },
    {
        "signup_id": "SU-005",
        "submitted_name": "Kim Jong Su",
        "date_of_birth": "1984-12-05",
        "country_code": "KP",
        "matched_entity_id": "WL-1005",
        "matched_name": "Jong Su Kim",
        "match_basis": "DOB+Country",
        "program": "UN 1718",
    },
    {
        "signup_id": "SU-009",
        "submitted_name": "Hasan Kadir",
        "date_of_birth": "1982-05-14",
        "country_code": "AE",
        "matched_entity_id": "WL-1006",
        "matched_name": "Hassan Qadir",
        "match_basis": "DOB+Country",
        "program": "OFAC SDN",
    },
    {
        "signup_id": "SU-011",
        "submitted_name": "Li Wai",
        "date_of_birth": "1988-01-19",
        "country_code": "HK",
        "matched_entity_id": "WL-1003",
        "matched_name": "Li Wei",
        "match_basis": "DOB+Country",
        "program": "UN 1718",
    },
    {
        "signup_id": "SU-012",
        "submitted_name": "Mohamad Hakim",
        "date_of_birth": "1980-06-30",
        "country_code": "SY",
        "matched_entity_id": "WL-1002",
        "matched_name": "Mohammad Al-Hakim",
        "match_basis": "Country",
        "program": "OFAC SDN",
    },
    {
        "signup_id": "SU-014",
        "submitted_name": "Aly Raza",
        "date_of_birth": "1991-03-22",
        "country_code": "PK",
        "matched_entity_id": "WL-1008",
        "matched_name": "Ali Raza",
        "match_basis": "Country",
        "program": "UK Sanctions List",
    },
]


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def main():
    if not os.path.exists(OUTPUT_PATH):
        fail(f"Missing output file: {OUTPUT_PATH}")

    with open(OUTPUT_PATH, "r", encoding="utf-8", newline="") as handle:
        first_line = handle.readline().rstrip("\r\n")
        actual_header = first_line.split("\t") if first_line else []
        if actual_header != EXPECTED_HEADER:
            fail(f"Header mismatch. Expected {EXPECTED_HEADER}, got {actual_header}")
        handle.seek(0)
        rows = list(csv.DictReader(handle, delimiter="\t"))

    if rows != EXPECTED_ROWS:
        fail(f"Output rows mismatch.\nExpected: {EXPECTED_ROWS}\nActual: {rows}")

    signup_ids = [row["signup_id"] for row in rows]
    if signup_ids != sorted(signup_ids):
        fail(f"Rows are not sorted by signup_id: {signup_ids}")

    print("All checks passed.")


if __name__ == "__main__":
    main()
