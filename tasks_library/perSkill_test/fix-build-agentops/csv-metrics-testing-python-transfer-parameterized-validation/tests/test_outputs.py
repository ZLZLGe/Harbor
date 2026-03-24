import ast
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path("/workspace/csv-metrics-lab")
REPORT_PATH = PROJECT_ROOT / "artifacts/csv-validation-regression-log.md"
TEST_FILE = PROJECT_ROOT / "tests/test_importer.py"


def _load_importer():
    sys.path.insert(0, str(PROJECT_ROOT))
    from csvmetrics.importer import ImportErrorDetail, MetricRecord, import_metrics

    return import_metrics, MetricRecord, ImportErrorDetail


def test_regression_log_exists_with_required_sections():
    assert REPORT_PATH.exists(), "Expected CSV validation log to be written"
    content = REPORT_PATH.read_text(encoding="utf-8").strip()
    assert len(content) > 140, "CSV validation log is too short"

    for heading in (
        "## Accepted rows",
        "## Rejected rows",
        "## Importer changes",
    ):
        assert heading in content, f"Missing artifact section: {heading}"

    assert "duplicate-header" in content, "Expected the log to mention duplicate headers"
    assert "invalid-number" in content, "Expected the log to mention malformed numeric values"


def test_project_tests_use_parameterized_valid_and_invalid_cases():
    assert TEST_FILE.exists(), "Expected importer test file to exist"

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

    assert len(param_lengths) >= 2, "Expected separate parameterized coverage blocks"
    assert max(param_lengths) >= 3, "Expected several CSV case variations"

    content = TEST_FILE.read_text(encoding="utf-8")
    assert "duplicate-header" in content, "Expected duplicate header coverage in project tests"
    assert "invalid-number" in content, "Expected malformed numeric coverage in project tests"
    assert "n/a" in content, "Expected a malformed numeric row example"
    assert "1e2" in content, "Expected a valid numeric edge case"


def test_importer_behavior_matches_validation_rules():
    import_metrics, MetricRecord, ImportErrorDetail = _load_importer()

    valid_result = import_metrics(
        "metric,value,unit\n"
        "requests,12,count\n"
        "latency,18.5,ms\n"
    )
    assert valid_result.records == [
        MetricRecord(metric="requests", value=12.0, unit="count"),
        MetricRecord(metric="latency", value=18.5, unit="ms"),
    ]
    assert valid_result.errors == []

    invalid_result = import_metrics(
        "metric,value,unit\n"
        "requests,12,count\n"
        "latency,n/a,ms\n"
    )
    assert invalid_result.records == [
        MetricRecord(metric="requests", value=12.0, unit="count"),
    ]
    assert invalid_result.errors == [
        ImportErrorDetail(
            line=3,
            code="invalid-number",
            message="invalid numeric value 'n/a' for metric 'latency'",
        )
    ]

    duplicate_result = import_metrics(
        "metric,value,value\n"
        "requests,12,count\n"
    )
    assert duplicate_result.records == []
    assert duplicate_result.errors == [
        ImportErrorDetail(
            line=1,
            code="duplicate-header",
            message="duplicate header: value",
        )
    ]


def test_full_project_test_suite_passes():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
