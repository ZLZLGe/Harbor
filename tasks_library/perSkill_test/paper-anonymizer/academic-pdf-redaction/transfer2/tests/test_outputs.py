import re
from pathlib import Path

import fitz

IN_DIR = Path("/root")
OUT_DIR = Path("/root/redacted/transfer2")
REPORT = Path("/root/reports/transfer2_quality.md")
FILES = ["paper2.pdf", "paper3.pdf"]

TOKENS = {
    "paper2.pdf": ["Jiatong Shi", "Carnegie Mellon", "10.21437/Interspeech.2024-33"],
    "paper3.pdf": ["Yueqian Lin", "Duke University", "Equal contribution"],
}


def text(path: Path) -> str:
    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def pages(path: Path) -> int:
    with fitz.open(path) as doc:
        return len(doc)


for fname in FILES:
    src = IN_DIR / fname
    out = OUT_DIR / fname
    assert out.exists(), f"Missing {out}"
    assert pages(src) == pages(out), f"Page count changed for {fname}"

    out_text = text(out)
    cutoff = out_text.lower().find("references")
    body = out_text if cutoff == -1 else out_text[:cutoff]
    body_low = body.lower()
    for token in TOKENS[fname]:
        assert token.lower() not in body_low, f"Token still visible in {fname}: {token}"

assert REPORT.exists(), "Missing transfer2 markdown report"
content = REPORT.read_text(encoding="utf-8")
assert "| file | original_chars | redacted_chars | retained_ratio | status |" in content

rows = [line for line in content.splitlines() if line.startswith("| paper")]
assert len(rows) == 2, "Report must have exactly two data rows"
for row in rows:
    ratio_match = re.search(r"\|\s*([0-9]+\.[0-9]{4})\s*\|\s*(PASS|FAIL)\s*\|$", row)
    assert ratio_match, f"Malformed row: {row}"
    ratio = float(ratio_match.group(1))
    status = ratio_match.group(2)
    assert ratio >= 0.75, f"Retention ratio too low: {ratio}"
    assert status == "PASS", f"Status must be PASS when ratio >= 0.75: {row}"
