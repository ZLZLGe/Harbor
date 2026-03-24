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
    result = ImportResult()
    reader = csv.DictReader(io.StringIO(csv_text.strip()))

    for line_number, row in enumerate(reader, start=2):
        metric = (row.get("metric") or "").strip()
        raw_value = (row.get("value") or "").strip()
        unit = (row.get("unit") or "").strip()

        try:
            value = float(raw_value) if raw_value else 0.0
        except ValueError:
            value = 0.0

        result.records.append(MetricRecord(metric=metric, value=value, unit=unit))

    return result
