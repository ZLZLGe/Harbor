import csv
import os
from pathlib import Path

INPUT_FIELDS = [
    'service_id',
    'framework',
    'needs_api',
    'needs_db',
    'needs_auth',
    'needs_external_service',
    'criticality',
]
OUTPUT_FIELDS = [
    'service_id',
    'framework',
    'unit_strategy',
    'api_strategy',
    'persistence_strategy',
    'isolation_strategy',
    'coverage_gate',
]


def resolve_workspace_root() -> Path:
    env_value = os.environ.get('WORKSPACE_ROOT')
    if env_value:
        return Path(env_value)
    return Path(__file__).resolve().parents[1] / 'workspace'


def coverage_gate(criticality: str) -> str:
    return {
        'critical': 'line>=95%;branch>=90%',
        'high': 'line>=90%;branch>=85%',
        'medium': 'line>=85%;branch>=75%',
        'low': 'line>=80%;branch>=70%',
    }[criticality]


def expected_row(row: dict[str, str]) -> dict[str, str]:
    framework = row['framework']
    needs_api = row['needs_api'] == 'yes'
    needs_db = row['needs_db'] == 'yes'
    needs_auth = row['needs_auth'] == 'yes'
    needs_external = row['needs_external_service'] == 'yes'

    if framework == 'django':
        unit_strategy = 'pytest-django unit tests with factory_boy'
        api_strategy = (
            'DRF APIClient tests with force_authenticate'
            if needs_api and needs_auth
            else 'DRF APIClient endpoint tests'
            if needs_api
            else 'pytest-django service tests without HTTP layer'
        )
        persistence_strategy = (
            'pytest-django transactional DB tests with factory_boy'
            if needs_db
            else 'repository seam tests without database access'
        )
        isolation_strategy = (
            'monkeypatch outbound clients and freeze side effects'
            if needs_external
            else 'fixture-scoped dependency isolation'
        )
    elif framework == 'laravel':
        unit_strategy = 'PHPUnit or Pest service tests with factories'
        api_strategy = (
            'Laravel HTTP tests with Sanctum actingAs and JSON assertions'
            if needs_api and needs_auth
            else 'Laravel HTTP JSON tests with response assertions'
            if needs_api
            else 'container-resolved unit tests without HTTP layer'
        )
        persistence_strategy = (
            'RefreshDatabase tests with model factories and assertDatabaseHas'
            if needs_db
            else 'repository contract tests with database fakes'
        )
        isolation_strategy = (
            'Http::fake plus Queue::fake boundary isolation'
            if needs_external
            else 'service container fakes for collaborator isolation'
        )
    elif framework == 'springboot':
        unit_strategy = 'JUnit5 and Mockito service-layer tests'
        api_strategy = (
            'MockMvc slice tests with security request post-processors'
            if needs_api and needs_auth
            else 'MockMvc controller tests with JSON assertions'
            if needs_api
            else 'JUnit5 service tests without web context'
        )
        persistence_strategy = (
            'DataJpaTest with Testcontainers-backed repository checks'
            if needs_db
            else 'Mockito repository doubles without persistence context'
        )
        isolation_strategy = (
            'WireMock stubs for external integrations'
            if needs_external
            else 'Mockito-driven collaborator isolation'
        )
    else:
        raise AssertionError(f'Unsupported framework: {framework}')

    return {
        'service_id': row['service_id'],
        'framework': framework,
        'unit_strategy': unit_strategy,
        'api_strategy': api_strategy,
        'persistence_strategy': persistence_strategy,
        'isolation_strategy': isolation_strategy,
        'coverage_gate': coverage_gate(row['criticality']),
    }


def test_outputs() -> None:
    workspace_root = resolve_workspace_root()
    input_path = workspace_root / 'input' / 'service_tdd_requirements.csv'
    output_path = workspace_root / 'output' / 'web_framework_tdd_matrix.csv'

    assert input_path.exists(), f'Missing input file: {input_path}'
    assert output_path.exists(), f'Missing output file: {output_path}'

    with input_path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == INPUT_FIELDS, f'Unexpected input header: {reader.fieldnames}'
        input_rows = list(reader)

    expected_rows = [expected_row(row) for row in input_rows]
    expected_rows.sort(key=lambda item: item['service_id'])

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
            assert value != '', f'{field} must not be empty'
            lowered = value.lower()
            assert lowered not in {'null', 'none', 'nan', 'n/a'}, f'{field} contains a null-like string'

    assert actual_rows == expected_rows, f'Output mismatch. Expected {expected_rows}, got {actual_rows}'


if __name__ == '__main__':
    test_outputs()
