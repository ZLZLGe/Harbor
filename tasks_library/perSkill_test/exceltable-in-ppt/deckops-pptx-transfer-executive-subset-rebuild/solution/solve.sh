#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import re
import subprocess
import zipfile
from xml.etree import ElementTree as ET

INPUT_FILE = "/root/enterprise-program-review.pptx"
OUTPUT_FILE = "/root/executive-subset-deck.pptx"
REARRANGE_SCRIPT = "/root/.codex/skills/pptx/scripts/rearrange.py"

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def cover_text(pptx_path: str) -> str:
    with zipfile.ZipFile(pptx_path, "r") as zf:
        root = ET.fromstring(zf.read("ppt/slides/slide1.xml"))
    texts = [node.text.strip() for node in root.iter(f"{{{A_NS}}}t") if node.text and node.text.strip()]
    return "\n".join(texts)


text = cover_text(INPUT_FILE)
match = re.search(r"Executive subset order:\s*slides?\s*([0-9,\s]+)\.", text)
if not match:
    raise SystemExit("Could not find the executive subset order on the cover slide.")

slide_numbers = [int(part.strip()) for part in match.group(1).split(",") if part.strip()]
sequence = ",".join(str(number - 1) for number in slide_numbers)

subprocess.run(
    ["python3", REARRANGE_SCRIPT, INPUT_FILE, OUTPUT_FILE, sequence],
    check=True,
)
PY
