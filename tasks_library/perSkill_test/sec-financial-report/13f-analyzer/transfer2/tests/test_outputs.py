import csv
from pathlib import Path


output = Path("/root/q3_crowding_watchlist.csv")
expected = Path("/tests/expected.csv")


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


assert output.exists(), "Missing /root/q3_crowding_watchlist.csv"
assert load_csv(output) == load_csv(expected)
