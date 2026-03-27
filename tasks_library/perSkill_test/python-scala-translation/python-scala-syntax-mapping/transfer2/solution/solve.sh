#!/bin/bash
set -euo pipefail

mkdir -p /outputs

python3 - <<'PY'
import json
from pathlib import Path

sections = json.loads(Path('/root/playbook_sections.json').read_text(encoding='utf-8'))

lines = ['# Python to Scala Migration Playbook', '']
for section in sections:
    lines.append(f"## {section['section']}")
    lines.append('| Python | Scala |')
    lines.append('|---|---|')
    for entry in section['entries']:
        lines.append(f"| `{entry['python']}` | `{entry['scala']}` |")
    lines.append('')

Path('/outputs/syntax_mapping_playbook.md').write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
PY
