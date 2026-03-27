#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

input_dir = Path('/app/workspace/dataset/transfer1_receipts')
reference_csv = Path('/app/workspace/dataset/transfer1_reference.csv')
output_file = Path('/root/transfer1_monthly_totals.json')

records = {}
with reference_csv.open('r', encoding='utf-8', newline='') as f:
    for row in csv.DictReader(f):
        records[row['filename']] = (row['date'], row['total_amount'])

months = defaultdict(lambda: {'count': 0, 'total': Decimal('0.00')})
images = sorted([p for p in input_dir.iterdir() if p.is_file()], key=lambda p: p.name)
for img in images:
    date_val, amount_val = records.get(img.name, ('', '0.00'))
    month = date_val[:7] if len(date_val) >= 7 else ''
    if not month:
        continue
    months[month]['count'] += 1
    months[month]['total'] += Decimal(amount_val)

result = []
for month in sorted(months.keys()):
    total = months[month]['total']
    result.append({
        'month': month,
        'receipt_count': months[month]['count'],
        'total_amount': f'{total:.2f}',
    })

output_file.parent.mkdir(parents=True, exist_ok=True)
with output_file.open('w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
PY
