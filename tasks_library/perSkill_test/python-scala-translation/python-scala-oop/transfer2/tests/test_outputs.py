import re
from pathlib import Path

p = Path("/app/workspace/transfer2.scala")
assert p.exists(), "missing /app/workspace/transfer2.scala"
text = p.read_text(encoding="utf-8")

patterns = [
    r"abstract\s+class\s+PaymentMethod",
    r"trait\s+Refundable",
    r"trait\s+Auditable",
    r"case\s+class\s+CardPayment",
    r"case\s+class\s+WirePayment",
    r"with\s+Refundable",
    r"with\s+Auditable",
    r"object\s+PaymentFactory",
    r"def\s+create\(",
]
for pat in patterns:
    assert re.search(pat, text), f"missing pattern: {pat}"

assert "class PaymentFactory" not in text, "factory should be modeled as companion-style object"
