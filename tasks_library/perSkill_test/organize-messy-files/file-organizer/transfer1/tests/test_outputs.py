import csv
import json
from pathlib import Path

PLAN = json.loads(Path('/root/data/organization_plan.json').read_text())
SOURCE_ROOT = Path('/root/media_drop')
ORGANIZED_ROOT = Path('/root/organized')
REPORT_PATH = Path('/root/transfer1_keep_decisions.csv')


def _duplicate_expectations():
    expected = {}
    for group in PLAN['duplicate_groups']:
        names = sorted(group['files'])
        canonical = names[0]
        for name in names:
            if name == canonical:
                expected[name] = ('keep', str(ORGANIZED_ROOT / group['category'] / name), group['group'])
            else:
                expected[name] = ('duplicate', str(ORGANIZED_ROOT / 'duplicates' / group['group'] / name), group['group'])
    return expected


def _unique_expectations():
    expected = {}
    for item in PLAN['unique_files']:
        name = item['file']
        expected[name] = ('unique', str(ORGANIZED_ROOT / item['category'] / name), '')
    return expected


def test_report_exists_and_rows_complete():
    assert REPORT_PATH.exists(), 'Missing /root/transfer1_keep_decisions.csv'
    with REPORT_PATH.open() as f:
        rows = list(csv.DictReader(f))

    expected = _duplicate_expectations() | _unique_expectations()
    assert len(rows) == len(expected)

    seen = set()
    for row in rows:
        name = row['file']
        assert name in expected, f'Unexpected file in report: {name}'
        decision, target, group = expected[name]
        assert row['decision'] == decision
        assert row['target'] == target
        assert row['group'] == group
        seen.add(name)

    assert seen == set(expected.keys())


def test_files_moved_to_expected_locations_and_source_empty():
    expected = _duplicate_expectations() | _unique_expectations()
    for name, (_decision, target, _group) in expected.items():
        assert Path(target).is_file(), f'Missing organized file for {name}: {target}'

    leftovers = [p.name for p in SOURCE_ROOT.glob('*') if p.is_file()]
    assert leftovers == [], f'Source folder still has files: {leftovers}'
