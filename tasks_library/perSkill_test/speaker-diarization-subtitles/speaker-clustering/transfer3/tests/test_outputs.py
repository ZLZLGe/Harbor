import csv
import json
from pathlib import Path


CONFIG = json.loads(Path("/root/data/task_config.json").read_text())


def load_table(path: Path):
    delimiter = "\t" if path.suffix == ".tsv" else ","
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def assert_matches(actual_path: Path, expected_path: Path):
    assert actual_path.exists(), f"Missing output file: {actual_path}"
    if actual_path.suffix in {".json"}:
        assert json.loads(actual_path.read_text()) == json.loads(expected_path.read_text())
        return
    if actual_path.suffix in {".csv", ".tsv"}:
        assert load_table(actual_path) == load_table(expected_path)
        return
    assert load_text(actual_path) == load_text(expected_path)


def test_primary_output_exists():
    assert Path(CONFIG["primary_output_file"]).exists()


def test_all_reference_files_match():
    for actual_file, expected_file in CONFIG["reference_files"].items():
        assert_matches(Path(actual_file), Path("/tests") / expected_file)
