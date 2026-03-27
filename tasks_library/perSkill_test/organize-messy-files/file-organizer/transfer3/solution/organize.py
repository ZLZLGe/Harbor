#!/usr/bin/env python3
import csv
import json
import shutil
from pathlib import Path

MANIFEST_PATH = Path('/root/data/finance_manifest.json')
SOURCE_ROOT = Path('/root/desk')
TARGET_ROOT = Path('/root/finance')
OUTPUT_PATH = Path('/root/transfer3_finance_index.csv')


def main() -> None:
    records = json.loads(MANIFEST_PATH.read_text())['records']
    rows: list[dict[str, str]] = []

    for item in records:
        filename = item['file']
        year = item['year']
        category = item['category']

        src = SOURCE_ROOT / filename
        if not src.exists():
            raise FileNotFoundError(f'Missing source file: {src}')

        dst = TARGET_ROOT / year / category / filename
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

        size_bytes = dst.stat().st_size
        rows.append({
            'year': year,
            'category': category,
            'file': filename,
            'target': str(dst),
            'size_bytes': str(size_bytes),
        })

    rows.sort(key=lambda r: (r['year'], r['category'], r['file']))
    with OUTPUT_PATH.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['year', 'category', 'file', 'target', 'size_bytes'])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
