from pathlib import Path


output = Path("/root/q3_manager_league.tsv")
expected = Path("/tests/expected.tsv")

assert output.exists(), "Missing /root/q3_manager_league.tsv"
assert output.read_text() == expected.read_text()
