from pathlib import Path

EXPECTED = Path("/tests/expected_station_channel_audit.csv").read_text(encoding="utf-8")

def test_transfer1_csv_matches_expected():
    output_path = Path("/root/transfer1_station_channel_audit.csv")
    assert output_path.exists(), "missing /root/transfer1_station_channel_audit.csv"
    assert output_path.read_text(encoding="utf-8") == EXPECTED
