import json
from pathlib import Path

import pandas as pd

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())
EXPECTED = json.loads(Path('/root/data/expected.json').read_text())


def test_output_files_exist():
    assert Path(CONFIG['output_file']).exists(), f"Missing output file: {CONFIG['output_file']}"
    assert Path(CONFIG['summary_file']).exists(), f"Missing summary file: {CONFIG['summary_file']}"


def test_anomaly_output_quality():
    df = pd.read_csv(CONFIG['output_file'])
    assert list(df.columns) == ['Category', 'Anomaly_Index']
    assert len(df) == EXPECTED['row_count']
    assert df['Category'].nunique() == len(df)
    assert df['Anomaly_Index'].between(-100, 100).all()
    assert df['Anomaly_Index'].is_monotonic_decreasing, 'Output must be sorted by descending anomaly index'

    top = df.iloc[0]
    bottom = df.iloc[-1]
    top_categories = EXPECTED.get('top_categories')
    if top_categories:
        assert top['Category'] in top_categories
    else:
        assert top['Category'] == EXPECTED['top_category']
    assert top['Anomaly_Index'] >= EXPECTED['top_min_anomaly']
    bottom_categories = EXPECTED.get('bottom_categories')
    if bottom_categories:
        assert bottom['Category'] in bottom_categories
    else:
        assert bottom['Category'] == EXPECTED['bottom_category']
    assert bottom['Anomaly_Index'] <= EXPECTED['bottom_max_anomaly']

    for check in EXPECTED.get('near_zero_categories', []):
        row = df[df['Category'] == check['category']]
        assert len(row) == 1
        assert abs(float(row.iloc[0]['Anomaly_Index'])) <= check['max_abs_anomaly']

    for check in EXPECTED.get('positive_categories', []):
        row = df[df['Category'] == check['category']]
        assert len(row) == 1
        assert float(row.iloc[0]['Anomaly_Index']) >= check['min_anomaly']

    for check in EXPECTED.get('negative_categories', []):
        row = df[df['Category'] == check['category']]
        assert len(row) == 1
        assert float(row.iloc[0]['Anomaly_Index']) <= check['max_anomaly']
