import ast
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path("/workspace/text-normalizer")
NOTE_PATH = PROJECT_ROOT / "artifacts/normalizer-regression-notes.md"
TEST_FILE = PROJECT_ROOT / "tests/test_normalizer.py"


def _load_normalizer():
    sys.path.insert(0, str(PROJECT_ROOT))
    from textnorm.normalizer import normalize_text

    return normalize_text


def test_notes_file_exists_with_required_sections():
    assert NOTE_PATH.exists(), "Expected regression notes to be written"
    content = NOTE_PATH.read_text(encoding="utf-8").strip()
    assert len(content) > 80, "Regression notes are too short"

    for heading in (
        "## Broken cases",
        "## Test updates",
        "## Implementation fix",
    ):
        assert heading in content, f"Missing notes section: {heading}"


def test_project_tests_use_parameterized_regression_cases():
    assert TEST_FILE.exists(), "Expected project test file to exist"

    module = ast.parse(TEST_FILE.read_text(encoding="utf-8"))
    param_lengths = []

    for node in ast.walk(module):
        if not isinstance(node, ast.FunctionDef):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr != "parametrize":
                continue
            if len(decorator.args) < 2:
                continue
            cases = decorator.args[1]
            if isinstance(cases, (ast.List, ast.Tuple)):
                param_lengths.append(len(cases.elts))

    assert param_lengths, "Expected at least one parametrized test"
    assert max(param_lengths) >= 4, "Expected several focused regression cases"

    content = TEST_FILE.read_text(encoding="utf-8")
    assert any(token in content for token in ("\\n", "\\t", "\\u00a0")), (
        "Expected tests to cover whitespace variations"
    )
    assert any(token in content for token in ("—", "–")), (
        "Expected tests to cover unicode dash behavior"
    )


def test_behavior_matches_documented_contract():
    normalize_text = _load_normalizer()

    assert normalize_text("  Monthly   Summary  ") == "Monthly Summary"
    assert normalize_text("Quarterly\nStatus") == "Quarterly Status"
    assert normalize_text("Client\u00a0Update") == "Client Update"
    assert normalize_text("Roadmap—Phase 2") == "Roadmap - Phase 2"
    assert normalize_text("Alpha\t—\nBeta") == "Alpha - Beta"


def test_full_project_test_suite_passes():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
