#!/bin/bash
set -euo pipefail

cd /workspace/release-portal

python3 - <<'PY'
from pathlib import Path

pom_path = Path("docs/pom.xml")
text = pom_path.read_text(encoding="utf-8")

old = """        <configuration>\n          <source>8</source>\n          <quiet>true</quiet>\n        </configuration>\n"""
new = """        <configuration>\n          <source>${maven.compiler.release}</source>\n          <doclint>none</doclint>\n          <quiet>true</quiet>\n        </configuration>\n"""

if old not in text:
    raise SystemExit("expected javadoc plugin configuration block was not found")

pom_path.write_text(text.replace(old, new), encoding="utf-8")
PY
