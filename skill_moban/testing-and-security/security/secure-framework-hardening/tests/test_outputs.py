import csv
import os
from pathlib import Path

INPUT_FIELDS = [
    'service',
    'framework',
    'auth_enabled',
    'input_validation',
    'csrf_protection',
    'rate_limit',
    'secrets_vault',
]
OUTPUT_FIELDS = ['service', 'risk_score', 'priority', 'missing_controls']
CONTROL_ORDER = [
    'auth_enabled',
    'input_validation',
    'csrf_protection',
    'rate_limit',
    'secrets_vault',
]


def resolve_workspace_root() -> Path:
    env_value = os.environ.get('WORKSPACE_ROOT')
    if env_value:
        return Path(env_value)
    return Path(__file__).resolve().parents[1] / 'workspace'


def expected_priority(risk_score: int) -> str:
    if risk_score >= 60:
        return 'critical'
    if risk_score >= 40:
        return 'high'
    if risk_score >= 20:
        return 'medium'
    return 'low'


def test_outputs() -> None:
    workspace_root = resolve_workspace_root()
    input_path = workspace_root / 'input' / 'security_controls.csv'
    output_path = workspace_root / 'output' / 'hardening_plan.csv'

    assert input_path.exists(), f'Missing input file: {input_path}'
    assert output_path.exists(), f'Missing output file: {output_path}'

    with input_path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == INPUT_FIELDS, f'Unexpected input header: {reader.fieldnames}'
        input_rows = list(reader)

    expected_rows = []
    for row in input_rows:
        missing = [control for control in CONTROL_ORDER if row[control] == 'no']
        risk_score = len(missing) * 20
        expected_rows.append(
            {
                'service': row['service'],
                'risk_score': str(risk_score),
                'priority': expected_priority(risk_score),
                'missing_controls': ';'.join(missing) if missing else 'none',
            }
        )

    expected_rows.sort(key=lambda item: (-int(item['risk_score']), item['service']))

    with output_path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        actual_rows = list(reader)
        actual_fields = reader.fieldnames

    assert actual_fields == OUTPUT_FIELDS, f'Unexpected output header: {actual_fields}'
    assert len(actual_rows) == len(expected_rows), 'Output row count mismatch'

    for row in actual_rows:
        assert list(row.keys()) == OUTPUT_FIELDS, 'Output field order mismatch'
        for field in OUTPUT_FIELDS:
            value = row[field]
            assert value is not None, f'{field} must not be null'
            assert value.lower() != 'null', f'{field} must not be null string'
            assert value.lower() != 'nan', f'{field} must not be nan'

    assert actual_rows == expected_rows, f'Output mismatch. Expected {expected_rows}, got {actual_rows}'


if __name__ == '__main__':
    test_outputs()
