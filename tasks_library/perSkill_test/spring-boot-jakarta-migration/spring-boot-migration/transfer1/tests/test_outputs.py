import json
import subprocess
from pathlib import Path

WORKSPACE = Path('/workspace')
CONFIG = json.loads(Path('/root/reference/task_config.json').read_text())


def assert_summary() -> None:
    summary_path = Path(CONFIG['summary_file'])
    assert summary_path.exists(), f'Missing summary file: {summary_path}'
    text = summary_path.read_text()
    for marker in CONFIG['summary_must_contain']:
        assert marker in text, f'Missing summary marker: {marker}'


def assert_files() -> None:
    for rule in CONFIG['file_expectations']:
        path = WORKSPACE / rule['path']
        assert path.exists(), f'Missing file: {path}'
        text = path.read_text()
        for needle in rule.get('must_contain', []):
            assert needle in text, f'{rule["path"]} is missing required content: {needle}'
        for needle in rule.get('must_not_contain', []):
            assert needle not in text, f'{rule["path"]} still contains forbidden content: {needle}'


def run_build() -> None:
    result = subprocess.run(
        CONFIG.get('build_command', ['mvn', '-q', 'test']),
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=CONFIG.get('build_timeout_sec', 300),
    )
    Path('/logs/verifier/build.log').write_text(result.stdout + '\n' + result.stderr)
    assert result.returncode == 0, f'Build/test command failed:\n{result.stdout}\n{result.stderr}'


if __name__ == '__main__':
    assert_summary()
    assert_files()
    run_build()
