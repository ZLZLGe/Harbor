import csv
import json
import os
import subprocess
import tempfile


CSV_PATH = "/root/output/geometry_audit.csv"


def load_expected():
    with tempfile.TemporaryDirectory(dir="/root") as temp_dir:
        ref_path = os.path.join(temp_dir, "reference_expected.mjs")
        with open("/tests/reference_expected.mjs", "r", encoding="utf-8") as src:
            with open(ref_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        output = subprocess.check_output(["node", ref_path], text=True)
        return json.loads(output)


def load_rows():
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_csv_exists():
    assert os.path.exists(CSV_PATH), f"Missing CSV: {CSV_PATH}"


def test_csv_matches_reference():
    expected = load_expected()
    actual = load_rows()
    assert actual == expected


def test_csv_is_sorted_and_complete():
    rows = load_rows()
    assert rows
    names = [row["name"] for row in rows]
    assert names == sorted(names)
    for row in rows:
        for field in [
            "min_x",
            "min_y",
            "min_z",
            "max_x",
            "max_y",
            "max_z",
        ]:
            assert "." in row[field]
            assert len(row[field].split(".")[1]) == 6
