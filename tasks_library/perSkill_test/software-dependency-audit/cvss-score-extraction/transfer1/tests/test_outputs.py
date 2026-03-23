import csv
import io
import json
from pathlib import Path


CONFIG = json.loads(Path("/root/data/task_config.json").read_text())
OUTPUT_PATH = Path(CONFIG["output_file"])


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_matches_expected():
    expected_path = Path(CONFIG["expected_file"])
    mode = CONFIG["mode"]
    if mode == "select_scores":
        assert json.loads(OUTPUT_PATH.read_text()) == json.loads(expected_path.read_text())
    elif mode == "gate_decisions":
        with OUTPUT_PATH.open(encoding="utf-8") as handle:
            generated = list(csv.DictReader(handle))
        with expected_path.open(encoding="utf-8") as handle:
            expected = list(csv.DictReader(handle))
        assert generated == expected
    elif mode == "provenance_brief":
        assert OUTPUT_PATH.read_text() == expected_path.read_text()
    elif mode == "package_matrix":
        generated = list(csv.DictReader(io.StringIO(OUTPUT_PATH.read_text()), delimiter="\t"))
        expected = list(csv.DictReader(io.StringIO(expected_path.read_text()), delimiter="\t"))
        assert generated == expected
    else:
        raise RuntimeError(f"Unsupported mode: {mode}")
