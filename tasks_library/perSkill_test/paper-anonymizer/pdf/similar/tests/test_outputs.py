import json
from pathlib import Path

from pypdf import PdfReader

PROFILE = Path("/root/reports/similar_document_profile.json")
EXPECTED = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]

assert PROFILE.exists(), "Missing profile JSON"
obj = json.loads(PROFILE.read_text(encoding="utf-8"))
assert "documents" in obj and isinstance(obj["documents"], list)
assert len(obj["documents"]) == 3

seen = set()
for item in obj["documents"]:
    file_name = item["file"]
    assert file_name in EXPECTED
    seen.add(file_name)

    reader = PdfReader(f"/root/{file_name}")
    full_text = "\n".join((p.extract_text() or "") for p in reader.pages)

    assert item["page_count"] == len(reader.pages)
    assert item["text_chars"] == len(full_text)
    assert 1 <= item["non_empty_pages"] <= len(reader.pages)
    assert isinstance(item["sample_excerpt"], str) and len(item["sample_excerpt"].strip()) > 0

assert seen == set(EXPECTED)
