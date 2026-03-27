#!/bin/bash
set -euo pipefail

mkdir -p /outputs

python3 - <<'PY'
import csv
from pathlib import Path

input_path = Path('/root/audit_candidates.csv')
output_path = Path('/outputs/syntax_mapping_audit.csv')

canonical = {
    'x = 5': 'val x = 5',
    'x: int = 5': 'val x: Int = 5',
    'for i in range(10): print(i)': 'for (i <- 0 until 10) println(i)',
    'f"Value: {x:.2f}"': 'f"Value: $x%.2f"',
    'user_active and not suspended': 'user_active && !suspended',
    'evens = [x for x in numbers if x % 2 == 0]': 'val evens = numbers.filter(_ % 2 == 0)'
}

rows = []
with input_path.open(newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        python_snippet = row['python']
        correct = canonical[python_snippet]
        rows.append({
            'case_id': row['case_id'],
            'python': python_snippet,
            'proposed_scala': row['proposed_scala'],
            'is_correct': 'true' if row['proposed_scala'] == correct else 'false',
            'correct_scala': correct
        })

with output_path.open('w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(
        f,
        fieldnames=['case_id', 'python', 'proposed_scala', 'is_correct', 'correct_scala']
    )
    writer.writeheader()
    writer.writerows(rows)
PY
