#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
from pathlib import Path

input_dir = Path('/app/workspace/dataset/similar_receipts')
reference_csv = Path('/app/workspace/dataset/similar_reference.csv')
output_file = Path('/root/similar_receipt_rows.csv')

mapping = {}
with reference_csv.open('r', encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        mapping[row['filename']] = (row['date'], row['total_amount'])

images = sorted(
    [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png'}],
    key=lambda p: p.name,
)

output_file.parent.mkdir(parents=True, exist_ok=True)
with output_file.open('w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['filename', 'date', 'total_amount'])
    for img in images:
        d, a = mapping.get(img.name, ('', ''))
        writer.writerow([img.name, d, a])
PY
