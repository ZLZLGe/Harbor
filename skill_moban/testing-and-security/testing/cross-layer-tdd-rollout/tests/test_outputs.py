import csv
import os
from pathlib import Path

INPUT_FIELDS = [
    'feature_id',
    'user_role',
    'has_api',
    'has_ui',
    'has_external_service',
    'risk_level',
]
OUTPUT_FIELDS = [
    'feature_id',
    'user_journey',
    'unit_focus',
    'integration_focus',
    'e2e_focus',
    'coverage_gate',
    'checkpoint_plan',
]
CHECKPOINT_PLAN = 'journey-tests -> unit-red-green -> integration-red-green -> e2e-error-path -> coverage-gate'


def resolve_workspace_root() -> Path:
    env_value = os.environ.get('WORKSPACE_ROOT')
    if env_value:
        return Path(env_value)
    return Path(__file__).resolve().parents[1] / 'workspace'


def expected_user_journey(row: dict[str, str]) -> str:
    if row['has_ui'] == 'yes' and row['has_api'] == 'yes':
        return f"{row['user_role']} journey -> UI to API before code"
    if row['has_ui'] == 'yes':
        return f"{row['user_role']} journey -> UI interaction before code"
    if row['has_api'] == 'yes':
        return f"{row['user_role']} journey -> API flow before code"
    return f"{row['user_role']} journey -> offline workflow before code"


def expected_unit_focus(row: dict[str, str]) -> str:
    if row['has_ui'] == 'yes' and row['has_api'] == 'yes':
        return 'domain rules;UI state;API adapters;error paths'
    if row['has_ui'] == 'yes':
        return 'domain rules;UI state;error paths'
    if row['has_api'] == 'yes':
        return 'domain rules;API handlers;error paths'
    return 'domain rules;pure functions;error paths'


def expected_integration_focus(row: dict[str, str]) -> str:
    if row['has_external_service'] == 'yes' and row['has_api'] == 'yes':
        return 'API contracts;persistence;external failure path'
    if row['has_external_service'] == 'yes':
        return 'module seams;external failure path'
    if row['has_api'] == 'yes':
        return 'API contracts;persistence'
    return 'module seams only'


def expected_e2e_focus(row: dict[str, str]) -> str:
    if row['has_ui'] == 'yes' and row['has_external_service'] == 'yes':
        return 'happy path;dependency outage'
    if row['has_ui'] == 'yes' and row['has_api'] == 'yes':
        return 'happy path;API validation failure'
    if row['has_ui'] == 'yes':
        return 'happy path;client validation failure'
    if row['has_api'] == 'yes':
        return 'consumer smoke;auth failure'
    if row['has_external_service'] == 'yes':
        return 'orchestrator smoke;dependency outage'
    return 'batch smoke;invalid input'


def expected_coverage_gate(risk_level: str) -> str:
    mapping = {
        'critical': 'unit>=95%;integration>=90%;e2e=required',
        'high': 'unit>=90%;integration>=80%;e2e=required',
        'medium': 'unit>=85%;integration>=70%;e2e=targeted',
        'low': 'unit>=80%;integration>=60%;e2e=smoke',
    }
    return mapping[risk_level]


def test_outputs() -> None:
    workspace_root = resolve_workspace_root()
    input_path = workspace_root / 'input' / 'features.csv'
    output_path = workspace_root / 'output' / 'tdd_rollout.csv'

    assert input_path.exists(), f'Missing input file: {input_path}'
    assert output_path.exists(), f'Missing output file: {output_path}'

    with input_path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == INPUT_FIELDS, f'Unexpected input header: {reader.fieldnames}'
        input_rows = list(reader)

    expected_rows = []
    for row in input_rows:
        expected_rows.append(
            {
                'feature_id': row['feature_id'],
                'user_journey': expected_user_journey(row),
                'unit_focus': expected_unit_focus(row),
                'integration_focus': expected_integration_focus(row),
                'e2e_focus': expected_e2e_focus(row),
                'coverage_gate': expected_coverage_gate(row['risk_level']),
                'checkpoint_plan': CHECKPOINT_PLAN,
            }
        )

    expected_rows.sort(key=lambda item: item['feature_id'])

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
            assert value.strip() == value, f'{field} must not have leading or trailing spaces'
            assert value.lower() not in {'null', 'none', 'nan', 'n/a'}, f'{field} contains a null-like marker'

    assert actual_rows == expected_rows, f'Output mismatch. Expected {expected_rows}, got {actual_rows}'


if __name__ == '__main__':
    test_outputs()
