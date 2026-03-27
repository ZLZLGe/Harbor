import csv
from pathlib import Path

OUTPUT = Path("/root/admin_dashboard_request_matrix.csv")

EXPECTED_ROWS = [
    {
        "request_url": "http://localhost:3000/api/summary",
        "duration_ms": "420",
        "loading_pattern": "sequential",
        "criticality": "critical",
        "recommended_action": "start-in-parallel",
    },
    {
        "request_url": "http://localhost:3000/api/routes",
        "duration_ms": "310",
        "loading_pattern": "sequential",
        "criticality": "critical",
        "recommended_action": "start-in-parallel",
    },
    {
        "request_url": "http://localhost:3000/api/incidents",
        "duration_ms": "280",
        "loading_pattern": "sequential",
        "criticality": "critical",
        "recommended_action": "start-in-parallel",
    },
    {
        "request_url": "http://localhost:3000/api/weather",
        "duration_ms": "190",
        "loading_pattern": "sequential",
        "criticality": "progressive",
        "recommended_action": "defer-after-first-paint",
    },
    {
        "request_url": "http://localhost:3000/api/audit-log",
        "duration_ms": "260",
        "loading_pattern": "sequential",
        "criticality": "progressive",
        "recommended_action": "defer-until-tab-open",
    },
]


def main() -> None:
    assert OUTPUT.exists(), f"missing output file: {OUTPUT}"
    with OUTPUT.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == [
        "request_url",
        "duration_ms",
        "loading_pattern",
        "criticality",
        "recommended_action",
    ], reader.fieldnames
    assert rows == EXPECTED_ROWS, rows


if __name__ == "__main__":
    main()
