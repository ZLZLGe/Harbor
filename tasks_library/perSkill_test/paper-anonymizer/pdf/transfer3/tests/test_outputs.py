import re
from pathlib import Path

REPORT = Path("/root/reports/transfer3_keyword_inventory.md")
KEYWORDS = ["voice", "data", "pruning"]

assert REPORT.exists(), "Missing keyword inventory report"
content = REPORT.read_text(encoding="utf-8")
assert content.startswith("# Transfer3 Keyword Inventory"), "Missing required title"
assert "| keyword | paper1 | paper2 | paper3 | total |" in content

rows = [line for line in content.splitlines() if line.startswith("| ") and not line.startswith("| keyword") and not line.startswith("|---")]
assert len(rows) == 3, "Report must contain exactly 3 keyword rows"

seen = set()
for row in rows:
    m = re.match(r"\|\s*([a-z]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|$", row)
    assert m, f"Malformed row: {row}"

    kw = m.group(1)
    c1, c2, c3, total = map(int, m.groups()[1:])
    assert kw in KEYWORDS, f"Unexpected keyword {kw}"
    assert total == c1 + c2 + c3, f"Total mismatch for {kw}"
    seen.add(kw)

assert seen == set(KEYWORDS)
