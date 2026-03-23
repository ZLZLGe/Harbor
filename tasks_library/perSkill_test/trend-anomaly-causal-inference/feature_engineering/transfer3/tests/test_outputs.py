import json
from pathlib import Path

import pandas as pd

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())
EXPECTED = json.loads(Path('/root/data/expected.json').read_text())


def test_output_files_exist():
    assert Path(CONFIG['output_file']).exists()
    assert Path(CONFIG['summary_file']).exists()


def test_feature_table_quality():
    df = pd.read_csv(CONFIG['output_file'])
    id_col = CONFIG['id_column']

    assert len(df) == EXPECTED['row_count']
    assert id_col in df.columns

    for column in EXPECTED.get('required_columns', []):
        assert column in df.columns, f'Missing required column: {column}'

    for column in EXPECTED.get('removed_columns', []):
        assert column not in df.columns, f'Column should have been removed: {column}'

    numeric_columns = [column for column in df.columns if column != id_col]
    for column in numeric_columns:
        assert pd.api.types.is_numeric_dtype(df[column]), f'{column} must be numeric'
        assert df[column].notna().all(), f'{column} contains null values'

    for column in EXPECTED.get('binary_columns', []):
        observed = set(df[column].astype(float).unique())
        assert observed.issubset({0.0, 1.0}), f'{column} must be binary, got {observed}'

    for column in EXPECTED.get('minmax_columns', []):
        assert df[column].between(-1e-9, 1 + 1e-9).all(), f'{column} must be min-max scaled'

    for check in EXPECTED.get('value_checks', []):
        row = df[df[id_col].astype(str) == str(check['id'])]
        assert len(row) == 1
        observed = row.iloc[0][check['column']]
        if 'value' in check:
            assert observed == check['value']
        if 'min_value' in check:
            assert observed >= check['min_value']
        if 'max_value' in check:
            assert observed <= check['max_value']
