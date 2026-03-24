#!/bin/bash
set -euo pipefail

cd /workspace/csv-metrics-lab

cat <<'EOF' > csvmetrics/importer.py
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field


@dataclass(eq=True)
class MetricRecord:
    metric: str
    value: float
    unit: str


@dataclass(eq=True)
class ImportErrorDetail:
    line: int
    code: str
    message: str


@dataclass(eq=True)
class ImportResult:
    records: list[MetricRecord] = field(default_factory=list)
    errors: list[ImportErrorDetail] = field(default_factory=list)


def import_metrics(csv_text: str) -> ImportResult:
    rows = list(csv.reader(io.StringIO(csv_text.strip())))
    if not rows:
        return ImportResult()

    headers = [header.strip() for header in rows[0]]
    result = ImportResult()

    for header in headers:
        if headers.count(header) > 1:
            result.errors.append(
                ImportErrorDetail(
                    line=1,
                    code="duplicate-header",
                    message=f"duplicate header: {header}",
                )
            )
            return result

    for line_number, row in enumerate(rows[1:], start=2):
        values = [value.strip() for value in row]
        entry = dict(zip(headers, values))
        metric = entry["metric"]
        raw_value = entry["value"]
        unit = entry["unit"]

        try:
            numeric_value = float(raw_value)
        except ValueError:
            result.errors.append(
                ImportErrorDetail(
                    line=line_number,
                    code="invalid-number",
                    message=f"invalid numeric value '{raw_value}' for metric '{metric}'",
                )
            )
            continue

        result.records.append(
            MetricRecord(metric=metric, value=numeric_value, unit=unit)
        )

    return result
EOF

cat <<'EOF' > tests/test_importer.py
import pytest

from csvmetrics.importer import ImportErrorDetail, MetricRecord, import_metrics


@pytest.mark.parametrize(
    ("csv_text", "expected_records"),
    [
        (
            "metric,value,unit\nrequests,12,count\nlatency,18.5,ms\n",
            [
                MetricRecord(metric="requests", value=12.0, unit="count"),
                MetricRecord(metric="latency", value=18.5, unit="ms"),
            ],
        ),
        (
            "metric,value,unit\n requests , 7.25 , count \n",
            [
                MetricRecord(metric="requests", value=7.25, unit="count"),
            ],
        ),
        (
            "metric,value,unit\ncpu,1e2,percent\n",
            [
                MetricRecord(metric="cpu", value=100.0, unit="percent"),
            ],
        ),
    ],
)
def test_imports_accepted_rows(csv_text, expected_records):
    result = import_metrics(csv_text)

    assert result.records == expected_records
    assert result.errors == []


@pytest.mark.parametrize(
    ("csv_text", "expected_records", "expected_errors"),
    [
        (
            "metric,value,unit\nrequests,12,count\nlatency,n/a,ms\n",
            [
                MetricRecord(metric="requests", value=12.0, unit="count"),
            ],
            [
                ImportErrorDetail(
                    line=3,
                    code="invalid-number",
                    message="invalid numeric value 'n/a' for metric 'latency'",
                )
            ],
        ),
        (
            "metric,value,unit\nrequests, ,count\nerrors,4,count\n",
            [
                MetricRecord(metric="errors", value=4.0, unit="count"),
            ],
            [
                ImportErrorDetail(
                    line=2,
                    code="invalid-number",
                    message="invalid numeric value '' for metric 'requests'",
                )
            ],
        ),
        (
            "metric,value,value\nrequests,12,count\n",
            [],
            [
                ImportErrorDetail(
                    line=1,
                    code="duplicate-header",
                    message="duplicate header: value",
                )
            ],
        ),
    ],
)
def test_import_reports_rejected_rows(csv_text, expected_records, expected_errors):
    result = import_metrics(csv_text)

    assert result.records == expected_records
    assert result.errors == expected_errors
EOF

cat <<'EOF' > artifacts/csv-validation-regression-log.md
## Accepted rows

Covered compact case-driven imports for normal numeric rows, trimmed fields, and scientific notation so the importer keeps valid records in order.

## Rejected rows

Added rejected CSV cases for malformed numeric values and duplicate headers. Invalid numbers now surface row-level `invalid-number` errors, while duplicate headers stop the file with a `duplicate-header` error.

## Importer changes

Updated the importer to validate the header row before processing data rows, trim field values consistently, skip malformed numeric rows, and keep importing the remaining valid rows.
EOF

python -m pytest -q
