#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path("/root")
INBOX = ROOT / "inbox"
DESKS = ROOT / "desks"
OUTPUT = ROOT / "subject_inventory.json"

DESK_KEYWORDS = {
    "climate_transition": ["battery", "carbon", "solar", "heat pump", "emissions", "grid"],
    "consumer_ai": ["assistant", "retail", "shopping", "customer support", "checkout", "call center"],
    "public_health": ["clinic", "hospital", "vaccination", "wastewater", "asthma", "heat shelter"],
    "urban_mobility": ["bus lane", "commute", "cargo bike", "transit", "delivery", "street"],
}


def read_docx_text(path: Path) -> str:
    with ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    texts = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
    return " ".join(texts).lower()


def classify(text: str) -> str:
    scores = {}
    for desk, keywords in DESK_KEYWORDS.items():
        scores[desk] = sum(keyword in text for keyword in keywords)
    desk, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        raise ValueError(f"Unable to classify document text: {text[:120]}")
    return desk


inventory = {desk: [] for desk in DESK_KEYWORDS}

for docx_path in sorted(INBOX.glob("*.docx")):
    text = read_docx_text(docx_path)
    desk = classify(text)
    destination = DESKS / desk / docx_path.name
    shutil.move(str(docx_path), destination)
    inventory[desk].append(docx_path.name)

for filenames in inventory.values():
    filenames.sort()

OUTPUT.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n")
PY
