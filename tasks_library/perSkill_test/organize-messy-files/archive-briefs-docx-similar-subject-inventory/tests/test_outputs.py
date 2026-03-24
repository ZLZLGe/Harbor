import json
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


EXPECTED = {
    "climate_transition": ["brief_03.docx", "brief_07.docx"],
    "consumer_ai": ["brief_04.docx", "brief_06.docx"],
    "public_health": ["brief_01.docx", "brief_08.docx"],
    "urban_mobility": ["brief_02.docx", "brief_05.docx"],
}

DESK_KEYWORDS = {
    "climate_transition": ["battery", "carbon", "solar", "heat pump"],
    "consumer_ai": ["assistant", "shopping", "customer support", "checkout"],
    "public_health": ["clinic", "wastewater", "vaccination", "asthma"],
    "urban_mobility": ["bus lane", "cargo bike", "transit", "delivery"],
}

ROOT = Path("/root")
INBOX = ROOT / "inbox"
DESKS = ROOT / "desks"
OUTPUT = ROOT / "subject_inventory.json"


def read_docx_text(path: Path) -> str:
    with ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    texts = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
    return " ".join(texts).lower()


def test_inventory_file_and_directory_layout_match_expected():
    assert OUTPUT.is_file(), "Missing /root/subject_inventory.json"

    with OUTPUT.open() as handle:
        inventory = json.load(handle)

    assert inventory == EXPECTED

    actual = {}
    for desk in EXPECTED:
        desk_dir = DESKS / desk
        assert desk_dir.is_dir(), f"Missing desk directory: {desk_dir}"
        actual[desk] = sorted(path.name for path in desk_dir.glob("*.docx"))

    assert actual == EXPECTED
    assert sorted(path.name for path in INBOX.glob("*.docx")) == []


def test_files_remain_in_the_correct_topic_buckets():
    for desk, filenames in EXPECTED.items():
        keywords = DESK_KEYWORDS[desk]
        for filename in filenames:
            text = read_docx_text(DESKS / desk / filename)
            assert any(keyword in text for keyword in keywords), (
                f"{filename} landed in {desk}, but its text does not match that topic"
            )
