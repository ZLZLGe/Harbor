import csv
from pathlib import Path


OUTPUT_PATH = Path("/root/similar_request_audit.csv")

EXPECTED_ROWS = [
    {
        "frame_number": "4",
        "src_ip": "10.8.0.11",
        "src_port": "31001",
        "method": "POST",
        "uri": "/telemetry/v2/report",
        "tlm_mode": "exfil",
        "blob_length": "96",
        "sig_length": "64",
        "is_exfil_candidate": "true",
    },
    {
        "frame_number": "16",
        "src_ip": "10.8.0.12",
        "src_port": "31002",
        "method": "POST",
        "uri": "/telemetry/v2/report",
        "tlm_mode": "normal",
        "blob_length": "88",
        "sig_length": "64",
        "is_exfil_candidate": "false",
    },
    {
        "frame_number": "28",
        "src_ip": "10.8.0.13",
        "src_port": "31003",
        "method": "POST",
        "uri": "/telemetry/v2/report",
        "tlm_mode": "exfil",
        "blob_length": "72",
        "sig_length": "64",
        "is_exfil_candidate": "false",
    },
    {
        "frame_number": "40",
        "src_ip": "10.8.0.14",
        "src_port": "31004",
        "method": "GET",
        "uri": "/telemetry/v2/report",
        "tlm_mode": "exfil",
        "blob_length": "0",
        "sig_length": "0",
        "is_exfil_candidate": "false",
    },
]


def load_rows() -> list[dict[str, str]]:
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    with OUTPUT_PATH.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def test_header_order():
    rows = load_rows()
    assert rows, "expected at least one audit row"
    assert list(rows[0].keys()) == [
        "frame_number",
        "src_ip",
        "src_port",
        "method",
        "uri",
        "tlm_mode",
        "blob_length",
        "sig_length",
        "is_exfil_candidate",
    ]


def test_expected_rows():
    assert load_rows() == EXPECTED_ROWS


def main() -> None:
    test_header_order()
    test_expected_rows()
    print("similar verifier checks passed")


if __name__ == "__main__":
    main()
