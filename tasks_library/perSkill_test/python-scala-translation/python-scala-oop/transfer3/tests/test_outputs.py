import re
from pathlib import Path

p = Path("/app/workspace/transfer3.scala")
assert p.exists(), "missing /app/workspace/transfer3.scala"
text = p.read_text(encoding="utf-8")

patterns = [
    r"trait\s+Plugin",
    r"case\s+class\s+PluginResult\(",
    r"class\s+EchoPlugin\s+extends\s+Plugin",
    r"class\s+UpperPlugin\s+extends\s+Plugin",
    r"class\s+PluginRegistry",
    r"def\s+register\(",
    r"def\s+execute\(",
    r"object\s+PluginRegistry",
    r"def\s+fromDefaults\(",
]
for pat in patterns:
    assert re.search(pat, text), f"missing pattern: {pat}"

assert "from_defaults" not in text, "expected Scala naming style (fromDefaults)"
assert "dict[" not in text, "python type syntax should not appear in Scala output"
