import csv
from pathlib import Path

OUTPUT_FILE = Path("/root/form_markup_counts.tsv")
EXPECTED_HEADER = [
    "page_id",
    "page_file",
    "paid_stamps",
    "review_stamps",
    "warning_stickers",
    "total_markups",
]
EXPECTED_ROWS = [
    {
        "page_id": "page_001",
        "page_file": "/root/form_pages/page_001.pgm",
        "paid_stamps": "2",
        "review_stamps": "1",
        "warning_stickers": "2",
        "total_markups": "5",
    },
    {
        "page_id": "page_002",
        "page_file": "/root/form_pages/page_002.pgm",
        "paid_stamps": "3",
        "review_stamps": "2",
        "warning_stickers": "1",
        "total_markups": "6",
    },
    {
        "page_id": "page_003",
        "page_file": "/root/form_pages/page_003.pgm",
        "paid_stamps": "1",
        "review_stamps": "3",
        "warning_stickers": "0",
        "total_markups": "4",
    },
    {
        "page_id": "page_004",
        "page_file": "/root/form_pages/page_004.pgm",
        "paid_stamps": "0",
        "review_stamps": "1",
        "warning_stickers": "3",
        "total_markups": "4",
    },
]
EXPECTED_TOTAL = {
    "page_id": "TOTAL",
    "page_file": "ALL_PAGES",
    "paid_stamps": "6",
    "review_stamps": "7",
    "warning_stickers": "6",
    "total_markups": "19",
}


class TestFormMarkupCounts:
    def test_output_exists(self):
        assert OUTPUT_FILE.is_file()

    def test_tsv_content(self):
        with OUTPUT_FILE.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            assert reader.fieldnames == EXPECTED_HEADER
            rows = list(reader)

        assert rows[:-1] == EXPECTED_ROWS
        assert rows[-1] == EXPECTED_TOTAL

    def test_totals_are_consistent(self):
        with OUTPUT_FILE.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            rows = list(reader)

        page_rows = rows[:-1]
        total_row = rows[-1]
        paid = 0
        review = 0
        warning = 0

        for row in page_rows:
            page_total = (
                int(row["paid_stamps"])
                + int(row["review_stamps"])
                + int(row["warning_stickers"])
            )
            assert int(row["total_markups"]) == page_total
            assert Path(row["page_file"]).is_file()
            paid += int(row["paid_stamps"])
            review += int(row["review_stamps"])
            warning += int(row["warning_stickers"])

        assert int(total_row["paid_stamps"]) == paid
        assert int(total_row["review_stamps"]) == review
        assert int(total_row["warning_stickers"]) == warning
        assert int(total_row["total_markups"]) == paid + review + warning
