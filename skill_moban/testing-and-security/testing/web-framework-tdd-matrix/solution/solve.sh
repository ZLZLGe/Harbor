#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from pathlib import Path

workspace_root = Path(os.environ.get('WORKSPACE_ROOT', '/app/workspace'))
input_path = workspace_root / 'input' / 'service_tdd_requirements.csv'
output_dir = workspace_root / 'output'
output_path = output_dir / 'web_framework_tdd_matrix.csv'
output_dir.mkdir(parents=True, exist_ok=True)

output_fields = [
    'service_id',
    'framework',
    'unit_strategy',
    'api_strategy',
    'persistence_strategy',
    'isolation_strategy',
    'coverage_gate',
]


def coverage_gate(criticality: str) -> str:
    return {
        'critical': 'line>=95%;branch>=90%',
        'high': 'line>=90%;branch>=85%',
        'medium': 'line>=85%;branch>=75%',
        'low': 'line>=80%;branch>=70%',
    }[criticality]


def matrix_row(row: dict[str, str]) -> dict[str, str]:
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
        raise ValueError(f'Unsupported framework: {framework}')

    return {
        'service_id': row['service_id'],
        'framework': framework,
        'unit_strategy': unit_strategy,
        'api_strategy': api_strategy,
        'persistence_strategy': persistence_strategy,
        'isolation_strategy': isolation_strategy,
        'coverage_gate': coverage_gate(row['criticality']),
    }


with input_path.open('r', encoding='utf-8', newline='') as f:
    reader = csv.DictReader(f)
    rows = [matrix_row(row) for row in reader]

rows.sort(key=lambda item: item['service_id'])

with output_path.open('w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=output_fields)
    writer.writeheader()
    writer.writerows(rows)
PY
