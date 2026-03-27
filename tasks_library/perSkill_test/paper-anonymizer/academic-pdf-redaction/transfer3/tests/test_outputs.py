import json
from pathlib import Path

import fitz

OUT_DIR = Path("/root/redacted/transfer3")
MANIFEST = Path("/root/reports/transfer3_manifest.json")

EXPECTED_FILES = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
BASIC_TOKENS = {
    "paper1.pdf": ["Yueqian Lin", "arXiv:2509.26542"],
    "paper2.pdf": ["Jiatong Shi", "10.21437/Interspeech.2024-33"],
    "paper3.pdf": ["Yueqian Lin", "Equal contribution"],
}


def extract_text(path: Path) -> str:
    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


assert MANIFEST.exists(), "Missing manifest JSON"
obj = json.loads(MANIFEST.read_text(encoding="utf-8"))
assert isinstance(obj, dict) and "documents" in obj
assert isinstance(obj["documents"], list) and len(obj["documents"]) == 3

seen = set()
for row in obj["documents"]:
    file_name = row["file"]
    assert file_name in EXPECTED_FILES
    seen.add(file_name)

    assert isinstance(row["author_tokens_removed"], int) and row["author_tokens_removed"] >= 1
    assert isinstance(row["identifier_tokens_removed"], int) and row["identifier_tokens_removed"] >= 1
    assert isinstance(row["page_count_unchanged"], bool) and row["page_count_unchanged"]
    assert float(row["retained_ratio"]) >= 0.75

    out_pdf = OUT_DIR / file_name
    assert out_pdf.exists(), f"Missing {out_pdf}"
    text = extract_text(out_pdf)
    cutoff = text.lower().find("references")
    body = text if cutoff == -1 else text[:cutoff]
    low = body.lower()
    for token in BASIC_TOKENS[file_name]:
        assert token.lower() not in low, f"Token still visible in {file_name}: {token}"

assert seen == set(EXPECTED_FILES)
