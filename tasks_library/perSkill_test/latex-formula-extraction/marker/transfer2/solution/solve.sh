#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
from pathlib import Path

in_path = Path('/root/input/page_blocks.json')
out_path = Path('/root/transfer2_page_formula_counts.csv')

pages = json.loads(in_path.read_text(encoding='utf-8'))

with out_path.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['page', 'display_formula_count', 'formula_ids'])
    for page in pages:
        ids = [blk['id'] for blk in page.get('blocks', []) if blk.get('type') == 'display_formula']
        writer.writerow([page['page'], len(ids), ';'.join(ids)])
PY
