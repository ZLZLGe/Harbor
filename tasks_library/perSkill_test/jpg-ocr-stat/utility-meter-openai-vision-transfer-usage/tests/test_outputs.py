import csv
import hashlib
import io
import os
import re


OUTPUT_FILE = "/app/workspace/meter_usage.csv"
EXPECTED_HEADER = ["meter_id", "start_reading", "end_reading", "consumption"]
EXPECTED_CANONICAL_SHA256 = "4627e7ff366685b1f9eda104ae3afe630150210e844da18a6a199d6817181849"


def read_csv_rows(path: str) -> list[list[str]]:
    with open(path, newline="") as handle:
        return list(csv.reader(handle))


def canonical_csv_digest(rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    return hashlib.sha256(buffer.getvalue().encode("utf-8")).hexdigest()


def test_output_contract() -> None:
    assert os.path.exists(OUTPUT_FILE), "Missing /app/workspace/meter_usage.csv"

    actual_rows = read_csv_rows(OUTPUT_FILE)

    assert actual_rows, "CSV is empty."
    assert actual_rows[0] == EXPECTED_HEADER, (
        "Header mismatch.\n"
        f"Actual: {actual_rows[0]}\n"
        f"Expected: {EXPECTED_HEADER}"
    )

    for row in actual_rows:
        assert len(row) == 4, f"Each CSV row must contain exactly 4 columns: {row}"

    data_rows = actual_rows[1:]
    meter_ids = [row[0] for row in data_rows]
    assert meter_ids == sorted(meter_ids), (
        "Rows must be sorted by meter_id.\n"
        f"Actual order: {meter_ids}"
    )

    for meter_id, start_reading, end_reading, consumption in data_rows:
        assert meter_id, "meter_id must not be blank."
        assert re.fullmatch(r"\d{6}", start_reading), (
            "start_reading must be a 6-digit integer string.\n"
            f"Actual: {start_reading!r}"
        )
        assert re.fullmatch(r"\d{6}", end_reading), (
            "end_reading must be a 6-digit integer string.\n"
            f"Actual: {end_reading!r}"
        )
        assert re.fullmatch(r"(0|[1-9]\d*)", consumption), (
            "consumption must be a non-negative integer string without leading zeros.\n"
            f"Actual: {consumption!r}"
        )
        assert int(end_reading) >= int(start_reading), (
            "end_reading must be greater than or equal to start_reading.\n"
            f"meter_id={meter_id!r}, start={start_reading!r}, end={end_reading!r}"
        )
        assert int(end_reading) - int(start_reading) == int(consumption), (
            "consumption must equal end_reading - start_reading.\n"
            f"meter_id={meter_id!r}, start={start_reading!r}, end={end_reading!r}, consumption={consumption!r}"
        )

    assert canonical_csv_digest(actual_rows) == EXPECTED_CANONICAL_SHA256, (
        "CSV content is incorrect.\n"
        f"Actual rows: {actual_rows}"
    )
