#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

input_dir = Path('/app/workspace/dataset/transfer3_receipts')
reference_csv = Path('/app/workspace/dataset/transfer3_reference.csv')
output_file = Path('/root/transfer3_weekday_report.tsv')

records = {}
with reference_csv.open('r', encoding='utf-8', newline='') as f:
    for row in csv.DictReader(f):
        records[row['filename']] = (row['date'], Decimal(row['total_amount']))

weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
stats = {d: {'count': 0, 'total': Decimal('0.00')} for d in weekday_order}

images = sorted([p for p in input_dir.iterdir() if p.is_file()], key=lambda p: p.name)
for img in images:
    date_val, amount = records.get(img.name, ('', Decimal('0.00')))
    if not date_val:
        continue
    weekday = datetime.strptime(date_val, '%Y-%m-%d').strftime('%A')
    stats[weekday]['count'] += 1
    stats[weekday]['total'] += amount

all_count = sum(v['count'] for v in stats.values())
all_total = sum(v['total'] for v in stats.values())
all_avg = (all_total / Decimal(all_count)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if all_count else Decimal('0.00')

output_file.parent.mkdir(parents=True, exist_ok=True)
with output_file.open('w', encoding='utf-8', newline='') as f:
    f.write('weekday\treceipt_count\ttotal_amount\taverage_amount\n')
    for day in weekday_order:
        count = stats[day]['count']
        total = stats[day]['total']
        avg = (total / Decimal(count)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if count else Decimal('0.00')
        f.write(f'{day}\t{count}\t{total:.2f}\t{avg:.2f}\n')
    f.write(f'TOTAL\t{all_count}\t{all_total:.2f}\t{all_avg:.2f}\n')
PY
