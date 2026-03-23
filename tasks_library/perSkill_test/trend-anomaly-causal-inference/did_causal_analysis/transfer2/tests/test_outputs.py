import json
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())
EXPECTED = json.loads(Path('/root/data/expected.json').read_text())


def test_report_exists():
    assert Path(CONFIG['output_file']).exists()


def test_report_quality():
    report = json.loads(Path(CONFIG['output_file']).read_text())
    for key in ['intensive_margin', 'extensive_margin']:
        assert key in report
        assert len(report[key]) == EXPECTED['top_n']
        estimates = [entry['did_estimate'] for entry in report[key]]
        assert estimates == sorted(estimates, reverse=not CONFIG.get('ascending', False))
        for entry in report[key]:
            assert entry['method'] == EXPECTED['expected_method']

    observed_intensive = [entry['feature'] for entry in report['intensive_margin']]
    observed_extensive = [entry['feature'] for entry in report['extensive_margin']]
    assert observed_intensive == EXPECTED['intensive_features']
    assert observed_extensive == EXPECTED['extensive_features']

    for check in EXPECTED.get('min_estimates', []):
        pool = report[check['section']]
        match = next(entry for entry in pool if entry['feature'] == check['feature'])
        assert match['did_estimate'] >= check['min_value']
