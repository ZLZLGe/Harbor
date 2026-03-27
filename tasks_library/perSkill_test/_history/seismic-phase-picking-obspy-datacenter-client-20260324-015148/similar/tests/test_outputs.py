import json
from pathlib import Path

EXPECTED_CSV = Path("/tests/expected_metrics.csv").read_text(encoding="utf-8")
EXPECTED_SUMMARY = json.loads(Path("/tests/expected_summary.json").read_text(encoding="utf-8"))

def test_metrics_csv_matches_expected():
    output_path = Path("/root/similar_waveform_metrics.csv")
    assert output_path.exists(), "missing /root/similar_waveform_metrics.csv"
    assert output_path.read_text(encoding="utf-8") == EXPECTED_CSV

def test_summary_json_matches_expected():
    output_path = Path("/root/similar_waveform_summary.json")
    assert output_path.exists(), "missing /root/similar_waveform_summary.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == EXPECTED_SUMMARY
