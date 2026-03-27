from pathlib import Path

EXPECTED = Path("/tests/expected_response_plan.csv").read_text(encoding="utf-8")

def test_transfer3_csv_matches_expected():
    output_path = Path("/root/transfer3_response_plan.csv")
    assert output_path.exists(), "missing /root/transfer3_response_plan.csv"
    assert output_path.read_text(encoding="utf-8") == EXPECTED
