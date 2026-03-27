import json
from collections import Counter
from pathlib import Path

SPEC = json.loads(Path('/root/data/archive_spec.json').read_text())
SOURCE_ROOT = Path('/root/project_dump')
TARGET_ROOT = Path('/root/projects_sorted')
OUTPUT_PATH = Path('/root/transfer2_archive_plan.json')


def test_output_manifest_is_correct():
    assert OUTPUT_PATH.exists(), 'Missing /root/transfer2_archive_plan.json'
    report = json.loads(OUTPUT_PATH.read_text())

    records = SPEC['records']
    expected_total = len(records)

    bucket_counts = Counter(item['bucket'] for item in records)
    project_counts = Counter(item['project'] for item in records)
    destinations = sorted(
        str(TARGET_ROOT / item['bucket'] / item['project'] / item['file'])
        for item in records
    )

    assert report['total_files'] == expected_total
    assert report['bucket_counts'] == dict(sorted(bucket_counts.items()))
    assert report['project_counts'] == dict(sorted(project_counts.items()))
    assert report['destinations'] == destinations


def test_files_moved_and_source_cleared():
    for item in SPEC['records']:
        dst = TARGET_ROOT / item['bucket'] / item['project'] / item['file']
        assert dst.is_file(), f'Missing moved file: {dst}'

    leftovers = [
        item['file']
        for item in SPEC['records']
        if (SOURCE_ROOT / item['file']).exists()
    ]
    assert leftovers == [], f'Source still has listed files: {leftovers}'
