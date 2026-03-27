import json
from pathlib import Path

from pypdf import PdfReader

PACKET = Path("/root/output/transfer1_packet.pdf")
INDEX = Path("/root/reports/transfer1_packet_index.json")
EXPECTED_FILES = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]

assert PACKET.exists(), "Missing merged packet"
reader = PdfReader(str(PACKET))
assert len(reader.pages) == 3, "Packet must contain exactly 3 pages"

assert INDEX.exists(), "Missing packet index JSON"
obj = json.loads(INDEX.read_text(encoding="utf-8"))
assert "pages" in obj and isinstance(obj["pages"], list)
assert len(obj["pages"]) == 3

for i, row in enumerate(obj["pages"], start=1):
    assert row["packet_page"] == i
    assert row["source_file"] == EXPECTED_FILES[i - 1]
    assert row["source_page"] == 1

for page in reader.pages:
    text = (page.extract_text() or "").strip()
    assert len(text) > 20, "Merged page appears empty"
