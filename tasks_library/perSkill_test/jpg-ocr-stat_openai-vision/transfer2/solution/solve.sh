#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

input_dir = Path('/app/workspace/dataset/transfer2_receipts')
reference_csv = Path('/app/workspace/dataset/transfer2_reference.csv')
output_file = Path('/root/transfer2_amount_bands.csv')

records = {}
with reference_csv.open('r', encoding='utf-8', newline='') as f:
    for row in csv.DictReader(f):
        records[row['filename']] = Decimal(row['total_amount'])

bands = {
    'low_lt_20': {'count': 0, 'total': Decimal('0.00')},
    'mid_20_to_99_99': {'count': 0, 'total': Decimal('0.00')},
    'high_ge_100': {'count': 0, 'total': Decimal('0.00')},
}

images = sorted([p for p in input_dir.iterdir() if p.is_file()], key=lambda p: p.name)
for img in images:
    amount = records.get(img.name, Decimal('0.00'))
    if amount < Decimal('20.00'):
        key = 'low_lt_20'
    elif amount < Decimal('100.00'):
        key = 'mid_20_to_99_99'
    else:
        key = 'high_ge_100'
    bands[key]['count'] += 1
    bands[key]['total'] += amount

grand_total = sum(item['total'] for item in bands.values())
if grand_total == Decimal('0.00'):
    grand_total = Decimal('1.00')

order = ['low_lt_20', 'mid_20_to_99_99', 'high_ge_100']
output_file.parent.mkdir(parents=True, exist_ok=True)
with output_file.open('w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['band', 'receipt_count', 'total_amount', 'share_percent'])
    for key in order:
        total = bands[key]['total']
        share = (total * Decimal('100') / grand_total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        writer.writerow([
            key,
            str(bands[key]['count']),
            f'{total:.2f}',
            f'{share:.2f}',
        ])
PY
