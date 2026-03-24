import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT_DIR = Path(os.environ.get("SEMINAR_ROOT", "/root/seminar_drop"))
INBOX_DIR = ROOT_DIR / "inbox"
ORGANIZED_DIR = ROOT_DIR / "organized"
REPORT_PATH = ROOT_DIR / "reports" / "placement_manifest.json"

EXPECTED_CATEGORY_BY_FILE = {
    "archive_box_01.pdf": "causal_inference",
    "archive_box_02.pdf": "field_robotics",
    "archive_box_03.pdf": "climate_transition",
    "archive_box_04.pdf": "graph_learning",
    "archive_box_05.pdf": "causal_inference",
    "archive_box_06.pdf": "field_robotics",
    "archive_box_07.pdf": "climate_transition",
    "archive_box_08.pdf": "graph_learning",
    "archive_box_09.docx": "causal_inference",
    "archive_box_10.docx": "graph_learning",
    "archive_box_11.pptx": "field_robotics",
    "archive_box_12.pptx": "climate_transition",
}

EXPECTED_SHA256 = {
    "archive_box_01.pdf": "ed4deea61cb063b2c4916c8c1448708a4428eb3a45a45ba18342355692c049c5",
    "archive_box_02.pdf": "5a326ad6fc007ed78e22d5b20f88cf2dc66387f93cb39f330e07deb7f02aa481",
    "archive_box_03.pdf": "23374a8c16d11b1b2d36fca4a2bda91b209d3f676fb341bf861a0eba0e939fd8",
    "archive_box_04.pdf": "be2d6946592ecc2660af5603cb5eb560b3a8f4afb4f71f5ef13e95e31b4b52b6",
    "archive_box_05.pdf": "e56a55d7ae0a661bbfdbcd30a3c201393a0c768c25b269b4822d961ad9f249fc",
    "archive_box_06.pdf": "bc9627c347ffa0e89157b0cabf899419d3a66cfc9a75ab00d4e8b8c543aba10c",
    "archive_box_07.pdf": "67df4cba33723c9d062bd61c65603644ab94e0d4d9b4680442693c51b9b79d06",
    "archive_box_08.pdf": "2ea51c2b4bda4489402c5147b43ac7e09e9368a5c44e6a694cc91e703e5fd26a",
    "archive_box_09.docx": "cf18732aed6302e978dd05ac1f3c55332b2b600ae63bafa9785fc1ac6bebc15b",
    "archive_box_10.docx": "15235bbb57c80177eb586f437ec8c41e850b4556dd7f2af54fbec266d15c46fc",
    "archive_box_11.pptx": "b50cf9f12c9fa860a3fe4b91486efed3cddf28c35ecb99151598e8681daf1a93",
    "archive_box_12.pptx": "0270d2d861e4c05cb2d42e1e778a50e702566e7cbafed591a417cfe5462b1c77",
}

EXPECTED_FILES = sorted(EXPECTED_CATEGORY_BY_FILE)
EXPECTED_CATEGORIES = sorted(set(EXPECTED_CATEGORY_BY_FILE.values()))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest() -> list[dict[str, str]]:
    assert REPORT_PATH.exists(), f"Missing manifest: {REPORT_PATH}"
    data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list), "placement_manifest.json must contain a JSON array"
    return data


def test_category_directories_exist():
    for category in EXPECTED_CATEGORIES:
        assert (ORGANIZED_DIR / category).is_dir(), f"Missing category folder: {category}"


def test_files_are_organized_once_with_no_leftovers():
    found_paths = []
    for category in EXPECTED_CATEGORIES:
        folder = ORGANIZED_DIR / category
        found_paths.extend(path for path in folder.rglob("*") if path.is_file())

    found_names = sorted(path.name for path in found_paths)
    assert found_names == EXPECTED_FILES

    leftovers = sorted(path.name for path in INBOX_DIR.rglob("*") if path.is_file())
    assert leftovers == [], f"Inbox still contains files: {leftovers}"


def test_file_placement_matches_expected_topics():
    for file_name, category in EXPECTED_CATEGORY_BY_FILE.items():
        destination = ORGANIZED_DIR / category / file_name
        assert destination.is_file(), f"Missing organized file: {destination}"

    unexpected = []
    for path in ORGANIZED_DIR.rglob("*"):
        if path.is_file():
            expected_category = EXPECTED_CATEGORY_BY_FILE.get(path.name)
            if expected_category is None or path.parent.name != expected_category:
                unexpected.append(str(path))

    assert unexpected == [], f"Unexpected file placement: {unexpected}"


def test_manifest_schema_and_order():
    manifest = load_manifest()
    assert len(manifest) == len(EXPECTED_FILES)

    manifest_names = [entry.get("file_name") for entry in manifest]
    assert manifest_names == EXPECTED_FILES, "Manifest must be sorted by file_name"

    for entry in manifest:
        assert set(entry) == {"file_name", "category", "source", "destination", "sha256"}
        file_name = entry["file_name"]
        expected_category = EXPECTED_CATEGORY_BY_FILE[file_name]
        expected_source = str(INBOX_DIR / file_name)
        expected_destination = str(ORGANIZED_DIR / expected_category / file_name)

        assert entry["category"] == expected_category
        assert entry["source"] == expected_source
        assert entry["destination"] == expected_destination
        assert entry["sha256"] == EXPECTED_SHA256[file_name]


def test_manifest_matches_filesystem_state():
    manifest = load_manifest()

    for entry in manifest:
        destination = Path(entry["destination"])
        assert destination.is_file(), f"Manifest points to missing file: {destination}"
        assert sha256(destination) == entry["sha256"]


@pytest.mark.parametrize("file_name", EXPECTED_FILES)
def test_files_are_unmodified(file_name):
    category = EXPECTED_CATEGORY_BY_FILE[file_name]
    path = ORGANIZED_DIR / category / file_name
    assert sha256(path) == EXPECTED_SHA256[file_name]

    if path.suffix.lower() in {".docx", ".pptx"}:
        with ZipFile(path) as archive:
            assert archive.namelist(), f"Empty Office archive: {path}"
