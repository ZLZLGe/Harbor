import os
import re
from pathlib import Path

output = Path("/app/workspace/similar.scala")
assert output.exists(), "missing /app/workspace/similar.scala"
text = output.read_text(encoding="utf-8")

patterns = [
    r"sealed\s+trait\s+TokenType",
    r"case\s+class\s+Token\s*\(",
    r"def\s+withMetadata\s*\(",
    r"abstract\s+class\s+BaseTokenizer\[",
    r"def\s+tokenizeBatch\s*\(",
    r"class\s+StringTokenizer\s+extends\s+BaseTokenizer",
    r"class\s+NumericTokenizer\s+extends\s+BaseTokenizer",
    r"object\s+TokenizerBuilder",
    r"def\s+toToken\s*\(",
]

for pat in patterns:
    assert re.search(pat, text), f"missing pattern: {pat}"

assert "TODO" not in text, "output contains TODO"
assert text.count("override def tokenize") >= 2, "expected at least two concrete tokenize overrides"
