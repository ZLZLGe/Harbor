import re
from pathlib import Path

p = Path("/app/workspace/transfer1.scala")
assert p.exists(), "missing /app/workspace/transfer1.scala"
text = p.read_text(encoding="utf-8")

checks = [
    r"abstract\s+class\s+Job\(val\s+name:\s*String\)",
    r"case\s+class\s+CsvJob\(",
    r"case\s+class\s+ApiJob\(",
    r"override\s+def\s+run:\s*String",
    r"object\s+JobFactory",
    r"def\s+fromKind\(",
    r"object\s+JobRunner",
    r"def\s+runBatch\(",
]
for pat in checks:
    assert re.search(pat, text), f"missing pattern: {pat}"

assert "run_batch" not in text, "expected Scala naming style (runBatch)"
assert text.count("extends Job") >= 2, "expected at least two subclasses"
