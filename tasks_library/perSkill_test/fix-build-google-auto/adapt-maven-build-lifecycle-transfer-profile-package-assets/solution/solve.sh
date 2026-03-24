#!/bin/bash
set -euo pipefail

cd /workspace

python3 - <<'PY'
from pathlib import Path

path = Path("/workspace/app/pom.xml")
text = path.read_text()
needle = """<execution>
                                <id>stage-production-assets</id>
                                <phase>verify</phase>"""
replacement = """<execution>
                                <id>stage-production-assets</id>
                                <phase>process-resources</phase>"""

if needle not in text:
    raise SystemExit("expected stage-production-assets execution not found")

path.write_text(text.replace(needle, replacement, 1))
PY

mvn -q -B -f app/pom.xml -Pproduction package
