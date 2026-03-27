from pathlib import Path


OUTPUT_PATH = Path("/root/transfer2_lab_upload_summary.md")

EXPECTED = """# Lab Upload Summary
accepted_requests: 3
rejected_requests: 1

## Station Totals
- alpha: 2 accepted, 7168 bytes
- gamma: 1 accepted, 8192 bytes

## Largest Accepted Upload
frame_number: 40
station: gamma
specimen: S-130
bytes: 8192
"""


def test_expected_markdown():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    assert OUTPUT_PATH.read_text() == EXPECTED


def main() -> None:
    test_expected_markdown()
    print("transfer2 verifier checks passed")


if __name__ == "__main__":
    main()
