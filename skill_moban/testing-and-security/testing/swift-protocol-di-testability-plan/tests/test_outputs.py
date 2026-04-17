import csv
import os
from pathlib import Path

INPUT_FIELDS = [
    'component_id',
    'has_filesystem',
    'has_network',
    'has_external_api',
    'needs_preview_support',
    'needs_error_path',
]
OUTPUT_FIELDS = [
    'component_id',
    'protocol_split',
    'default_impls',
    'mock_plan',
    'injection_style',
    'test_focus',
    'concurrency_note',
]
PROTOCOL_RULES = [
    ('has_filesystem', 'FileSystemProviding', 'DefaultFileSystemProvider', 'MockFileSystemProvider'),
    ('has_network', 'NetworkTransporting', 'DefaultNetworkTransport', 'MockNetworkTransport'),
    ('has_external_api', 'ExternalAPIProviding', 'DefaultExternalAPIClient', 'MockExternalAPIClient'),
]


def resolve_workspace_root() -> Path:
    env_value = os.environ.get('WORKSPACE_ROOT')
    if env_value:
        return Path(env_value)
    return Path(__file__).resolve().parents[1] / 'workspace'


def is_yes(value: str) -> bool:
    return value.strip().lower() == 'yes'


def expected_row(row: dict[str, str]) -> dict[str, str]:
    protocols = []
    defaults = []
    mocks = []

    for field, protocol_name, default_name, mock_name in PROTOCOL_RULES:
        if is_yes(row[field]):
            protocols.append(protocol_name)
            defaults.append(default_name)
            mocks.append(mock_name)

    if protocols:
        protocol_split = ';'.join(protocols)
        default_impls = ';'.join(defaults)
        test_focus_parts = ['Use Swift Testing to cover success paths per protocol seam']
    else:
        protocol_split = 'Keep concrete core; extract protocols only for real external seams'
        default_impls = 'No live adapter needed'
        test_focus_parts = ['Use Swift Testing on pure logic without extra protocol mocks']

    mock_plan_parts = mocks[:] if mocks else ['Use direct value-based tests']

    if is_yes(row['needs_error_path']):
        mock_plan_parts.append('with configurable error cases')
        test_focus_parts.append('exercise thrown failures via mock error toggles')

    if is_yes(row['needs_preview_support']):
        injection_style = 'Initializer injection with default live adapters; override in tests and SwiftUI previews'
        test_focus_parts.append('verify preview wiring with injected stubs')
    else:
        injection_style = 'Initializer injection with default live adapters'

    if is_yes(row['has_network']) or is_yes(row['has_external_api']):
        concurrency_note = 'Protocols and mocks should be Sendable; keep async collaborators actor-safe'
    elif is_yes(row['has_filesystem']):
        concurrency_note = 'Make filesystem seams Sendable when crossing actor boundaries'
    else:
        concurrency_note = 'Only add Sendable if the type crosses concurrency boundaries'

    return {
        'component_id': row['component_id'],
        'protocol_split': protocol_split,
        'default_impls': default_impls,
        'mock_plan': ';'.join(mock_plan_parts),
        'injection_style': injection_style,
        'test_focus': ';'.join(test_focus_parts),
        'concurrency_note': concurrency_note,
    }


def test_outputs() -> None:
    workspace_root = resolve_workspace_root()
    input_path = workspace_root / 'input' / 'swift_components.csv'
    output_path = workspace_root / 'output' / 'swift_di_testability_plan.csv'

    assert input_path.exists(), f'Missing input file: {input_path}'
    assert output_path.exists(), f'Missing output file: {output_path}'

    with input_path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == INPUT_FIELDS, f'Unexpected input header: {reader.fieldnames}'
        input_rows = list(reader)

    expected_rows = sorted((expected_row(row) for row in input_rows), key=lambda item: item['component_id'])

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
            assert value.lower() not in {'null', 'none', 'nan', 'nil'}, f'{field} must not be a null-like string'

    assert actual_rows == expected_rows, f'Output mismatch. Expected {expected_rows}, got {actual_rows}'


if __name__ == '__main__':
    test_outputs()
