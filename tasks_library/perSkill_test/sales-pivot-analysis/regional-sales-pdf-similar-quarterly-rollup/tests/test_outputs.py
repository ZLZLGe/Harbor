#!/usr/bin/env python3

import pandas as pd
import pdfplumber

OUTPUT_FILE = "/root/regional_sales_rollup.csv"
INPUT_PDF = "/root/regional_sales_report_input"

MONTH_TO_QUARTER = {
    "Jan": "Q1",
    "Feb": "Q1",
    "Mar": "Q1",
    "Apr": "Q2",
    "May": "Q2",
    "Jun": "Q2",
}

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 3,
}

EXPECTED_COLUMNS = ["region", "quarter", "gross_sales", "refunds", "net_sales"]


def parse_expected_from_pdf():
    rows = []
    with pdfplumber.open(INPUT_PDF) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables(TABLE_SETTINGS):
                if not table:
                    continue
                header = [str(cell).strip() if cell else "" for cell in table[0]]
                start_idx = 1 if header[:5] == ["Region", "Month", "Gross Sales", "Refunds", "Net Sales"] else 0
                for raw_row in table[start_idx:]:
                    if not raw_row or len(raw_row) < 5:
                        continue
                    region, month, gross_sales, refunds, net_sales = [
                        str(cell).strip() if cell is not None else "" for cell in raw_row[:5]
                    ]
                    if not region or region == "Region" or month not in MONTH_TO_QUARTER:
                        continue
                    rows.append(
                        {
                            "region": region,
                            "quarter": MONTH_TO_QUARTER[month],
                            "gross_sales": int(gross_sales.replace(",", "")),
                            "refunds": int(refunds.replace(",", "")),
                            "net_sales": int(net_sales.replace(",", "")),
                        }
                    )

    return (
        pd.DataFrame(rows)
        .groupby(["region", "quarter"], as_index=False)[["gross_sales", "refunds", "net_sales"]]
        .sum()
        .sort_values(["region", "quarter"], kind="stable")
        .reset_index(drop=True)
    )


def test_output_file_exists():
    assert pd.io.common.file_exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"


def test_output_columns_and_order():
    actual = pd.read_csv(OUTPUT_FILE)
    assert list(actual.columns) == EXPECTED_COLUMNS


def test_output_matches_pdf_rollup():
    actual = pd.read_csv(OUTPUT_FILE)
    expected = parse_expected_from_pdf()

    actual = actual.sort_values(["region", "quarter"], kind="stable").reset_index(drop=True)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)


def test_output_is_sorted():
    actual = pd.read_csv(OUTPUT_FILE)
    sorted_actual = actual.sort_values(["region", "quarter"], kind="stable").reset_index(drop=True)
    pd.testing.assert_frame_equal(actual.reset_index(drop=True), sorted_actual, check_dtype=False)


def test_row_count_and_quarters():
    actual = pd.read_csv(OUTPUT_FILE)
    assert len(actual) == 8
    assert set(actual["quarter"]) == {"Q1", "Q2"}


def test_totals_match_source():
    actual = pd.read_csv(OUTPUT_FILE)
    expected = parse_expected_from_pdf()
    assert int(actual["gross_sales"].sum()) == int(expected["gross_sales"].sum())
    assert int(actual["refunds"].sum()) == int(expected["refunds"].sum())
    assert int(actual["net_sales"].sum()) == int(expected["net_sales"].sum())
