#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from pathlib import Path

PROTOCOL_RULES = [
    ('has_filesystem', 'FileSystemProviding', 'DefaultFileSystemProvider', 'MockFileSystemProvider'),
    ('has_network', 'NetworkTransporting', 'DefaultNetworkTransport', 'MockNetworkTransport'),
    ('has_external_api', 'ExternalAPIProviding', 'DefaultExternalAPIClient', 'MockExternalAPIClient'),
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


def is_yes(value: str) -> bool:
    return value.strip().lower() == 'yes'


def build_row(row: dict[str, str]) -> dict[str, str]:
    protocols = []
    defaults = []
    mocks = []

    for field, protocol_name, default_name, mock_name in PROTOCOL_RULES:
        if is_yes(row.get(field, '')):
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

    if is_yes(row.get('needs_error_path', '')):
        mock_plan_parts.append('with configurable error cases')
        test_focus_parts.append('exercise thrown failures via mock error toggles')

    if is_yes(row.get('needs_preview_support', '')):
        injection_style = 'Initializer injection with default live adapters; override in tests and SwiftUI previews'
        test_focus_parts.append('verify preview wiring with injected stubs')
    else:
        injection_style = 'Initializer injection with default live adapters'

    if is_yes(row.get('has_network', '')) or is_yes(row.get('has_external_api', '')):
        concurrency_note = 'Protocols and mocks should be Sendable; keep async collaborators actor-safe'
    elif is_yes(row.get('has_filesystem', '')):
        concurrency_note = 'Make filesystem seams Sendable when crossing actor boundaries'
    else:
        concurrency_note = 'Only add Sendable if the type crosses concurrency boundaries'

    return {
        'component_id': row.get('component_id', ''),
        'protocol_split': protocol_split,
        'default_impls': default_impls,
        'mock_plan': ';'.join(mock_plan_parts),
        'injection_style': injection_style,
        'test_focus': ';'.join(test_focus_parts),
        'concurrency_note': concurrency_note,
    }


workspace_root = Path(os.environ.get('WORKSPACE_ROOT', '/app/workspace'))
input_path = workspace_root / 'input' / 'swift_components.csv'
output_dir = workspace_root / 'output'
output_path = output_dir / 'swift_di_testability_plan.csv'
output_dir.mkdir(parents=True, exist_ok=True)

rows = []
with input_path.open('r', encoding='utf-8', newline='') as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        rows.append(build_row(row))

rows.sort(key=lambda item: item['component_id'])

with output_path.open('w', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
PY
