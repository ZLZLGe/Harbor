import hashlib
import json
from pathlib import Path

OUTPUT_PATH = Path("/root/covenant_breach_summary.json")
PDF_PATH = Path("/root/covenant_package.pdf")
XLSX_PATH = Path("/root/quarterly_financials.xlsx")

EXPECTED_OUTPUT = {
    "breach_periods": [
        {
            "test_period": "2024-09-30",
            "breaches": [
                {
                    "metric": "Fixed Charge Coverage Ratio",
                    "actual": 1.486,
                    "threshold": 1.55,
                    "breach_direction": "below_minimum",
                    "deviation": 0.064,
                }
            ],
        },
        {
            "test_period": "2024-12-31",
            "breaches": [
                {
                    "metric": "Fixed Charge Coverage Ratio",
                    "actual": 1.344,
                    "threshold": 1.55,
                    "breach_direction": "below_minimum",
                    "deviation": 0.206,
                }
            ],
        },
        {
            "test_period": "2025-06-30",
            "breaches": [
                {
                    "metric": "Total Net Leverage Ratio",
                    "actual": 4.698,
                    "threshold": 4.0,
                    "breach_direction": "above_maximum",
                    "deviation": 0.698,
                },
                {
                    "metric": "Senior Secured Leverage Ratio",
                    "actual": 3.348,
                    "threshold": 2.75,
                    "breach_direction": "above_maximum",
                    "deviation": 0.598,
                },
                {
                    "metric": "Fixed Charge Coverage Ratio",
                    "actual": 0.982,
                    "threshold": 1.65,
                    "breach_direction": "below_minimum",
                    "deviation": 0.668,
                },
            ],
        },
    ],
    "most_severe_breach": {
        "test_period": "2025-06-30",
        "metric": "Total Net Leverage Ratio",
        "actual": 4.698,
        "threshold": 4.0,
        "breach_direction": "above_maximum",
        "deviation": 0.698,
    },
}

EXPECTED_HASHES = {
    PDF_PATH: "24b7f92e012f20228df5873f4acbdd3ed94f761c04ba5d4a2cb01b048e2164f3",
    XLSX_PATH: "4e2f331266d9c13c43d7f15cad9fc82a1a053ba822b86c999258189309881d8c",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    assert PDF_PATH.exists(), f"Missing input file: {PDF_PATH}"
    assert XLSX_PATH.exists(), f"Missing input file: {XLSX_PATH}"
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"

    for path, expected_hash in EXPECTED_HASHES.items():
        actual_hash = sha256(path)
        assert actual_hash == expected_hash, f"Unexpected input hash for {path}: {actual_hash}"

    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        actual = json.load(f)

    assert actual == EXPECTED_OUTPUT, (
        "Output JSON did not match expectation.\n"
        f"Expected: {json.dumps(EXPECTED_OUTPUT, indent=2)}\n"
        f"Actual: {json.dumps(actual, indent=2)}"
    )


if __name__ == "__main__":
    main()
    print("All checks passed.")
