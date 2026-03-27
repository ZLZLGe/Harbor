import csv
import json
from pathlib import Path

MANIFEST = json.loads(Path('/root/data/finance_manifest.json').read_text())
SOURCE_ROOT = Path('/root/desk')
TARGET_ROOT = Path('/root/finance')
OUTPUT_PATH = Path('/root/transfer3_finance_index.csv')


def _expected_rows():
    rows = []
    for item in MANIFEST['records']:
        filename = item['file']
        year = item['year']
        category = item['category']
        target = TARGET_ROOT / year / category / filename
        rows.append((year, category, filename, str(target)))
    rows.sort()
    return rows


def test_index_exists_and_matches_manifest():
    assert OUTPUT_PATH.exists(), 'Missing /root/transfer3_finance_index.csv'

    with OUTPUT_PATH.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert reader.fieldnames == ['year', 'category', 'file', 'target', 'size_bytes']

    expected = _expected_rows()
    actual = [(r['year'], r['category'], r['file'], r['target']) for r in rows]
    assert actual == expected

    sorted_copy = sorted(actual)
    assert actual == sorted_copy, 'Rows must be sorted by year/category/file'

    for row in rows:
        target = Path(row['target'])
        assert target.is_file(), f"Missing target file: {target}"
        assert int(row['size_bytes']) == target.stat().st_size


def test_source_is_cleared_for_manifest_files():
    leftovers = [
        item['file']
        for item in MANIFEST['records']
        if (SOURCE_ROOT / item['file']).exists()
    ]
    assert leftovers == [], f'Source still contains listed files: {leftovers}'
