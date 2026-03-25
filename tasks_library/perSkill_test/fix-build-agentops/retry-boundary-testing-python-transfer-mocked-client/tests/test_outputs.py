import ast
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(
    os.environ.get("TASK_PROJECT_ROOT", "/workspace/billing-relay")
).resolve()
TEST_FILE = PROJECT_ROOT / "tests" / "test_billing_gateway.py"
REPORT_FILE = PROJECT_ROOT / "reports" / "mock_retry_audit.txt"

REQUIRED_SOURCE_TOKENS = [
    "InvoiceBillingGateway",
    "ChargeResult",
    "GatewayTimeoutError",
    "GatewayDeclinedError",
    "BillingDeclinedError",
    "BillingUnavailableError",
    "create_charge",
    "temporary timeout",
    "card expired",
    "3 attempts",
    "idempotency_key",
    "idem-inv-100",
    "duplicate",
    "call_count",
]

FORBIDDEN_SOURCE_TOKENS = [
    "requests",
    "httpx",
    "respx",
    "vcrpy",
    "subprocess",
    "time.sleep",
    "asyncio.sleep",
    "localhost",
    "127.0.0.1",
    "http://",
    "https://",
]

REQUIRED_REPORT_LINES = {
    "suite_status: complete",
    "tested_entrypoint: InvoiceBillingGateway.capture_invoice",
    "mock_boundary: create_charge",
    "retry_success_attempts: 3",
    "decline_mapping: BillingDeclinedError",
    "idempotent_repeat_observed: true",
}

COMMON_UNITTEST_MOCK_NAMES = {
    "patch",
    "Mock",
    "MagicMock",
    "AsyncMock",
    "create_autospec",
    "mock_open",
    "PropertyMock",
}


def run_command(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing else f"{src_path}:{existing}"
    return subprocess.run(
        list(args),
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        env=env,
    )


def is_fixture_decorator(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "fixture"
    if isinstance(node, ast.Attribute):
        return (
            node.attr == "fixture"
            and isinstance(node.value, ast.Name)
            and node.value.id == "pytest"
        )
    if isinstance(node, ast.Call):
        return is_fixture_decorator(node.func)
    return False


def attribute_chain(node: ast.expr) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return tuple(reversed(parts))
    return None


def uses_unittest_mock(tree: ast.AST) -> bool:
    unittest_roots: set[str] = set()
    mock_module_roots: set[str] = set()
    imported_mock_names: set[str] = set()
    has_wildcard_mock_import = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "unittest":
                    unittest_roots.add(alias.asname or "unittest")
                elif alias.name == "unittest.mock":
                    if alias.asname:
                        mock_module_roots.add(alias.asname)
                    else:
                        unittest_roots.add("unittest")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "unittest":
                for alias in node.names:
                    if alias.name == "mock":
                        mock_module_roots.add(alias.asname or "mock")
            elif node.module == "unittest.mock":
                for alias in node.names:
                    if alias.name == "*":
                        has_wildcard_mock_import = True
                    else:
                        imported_mock_names.add(alias.asname or alias.name)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        chain = attribute_chain(node.func)
        if not chain:
            continue

        root = chain[0]
        if root in imported_mock_names or root in mock_module_roots:
            return True
        if has_wildcard_mock_import and root in COMMON_UNITTEST_MOCK_NAMES:
            return True
        if root in unittest_roots and len(chain) >= 2 and chain[1] == "mock":
            return True

    return False


def test_authored_test_file_has_required_structure() -> None:
    assert TEST_FILE.exists(), "缺少 tests/test_billing_gateway.py"

    source = TEST_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    test_count = 0
    fixture_count = 0
    has_mocking = False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_count += 1
        if isinstance(node, ast.FunctionDef) and any(
            is_fixture_decorator(decorator) for decorator in node.decorator_list
        ):
            fixture_count += 1

    has_mocking = uses_unittest_mock(tree)

    assert test_count >= 4, "至少需要 4 个测试函数"
    assert fixture_count >= 1, "至少需要 1 个 pytest fixture"
    assert has_mocking, "需要在第三方边界使用 unittest.mock"


def test_authored_test_file_mentions_required_contracts() -> None:
    source = TEST_FILE.read_text(encoding="utf-8")

    for token in REQUIRED_SOURCE_TOKENS:
        assert token in source, f"测试文件里缺少关键契约内容: {token}"

    for token in FORBIDDEN_SOURCE_TOKENS:
        assert token not in source, f"测试文件里不应出现: {token}"


def test_mock_retry_audit_file_matches_required_lines() -> None:
    assert REPORT_FILE.exists(), "缺少 reports/mock_retry_audit.txt"

    lines = [line.strip() for line in REPORT_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines[0] == "Mock Retry Audit", "审计摘要首行不符合要求"

    for line in REQUIRED_REPORT_LINES:
        assert line in lines, f"审计摘要缺少: {line}"

    note_lines = [line for line in lines if "no real billing service" in line.lower()]
    assert note_lines, "审计摘要需要明确写到没有访问真实计费服务"


def test_authored_tests_collect_expected_cases() -> None:
    result = run_command(
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "tests/test_billing_gateway.py",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    collected = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("tests/test_billing_gateway.py::")
    ]
    assert len(collected) >= 4, result.stdout


def test_authored_tests_pass() -> None:
    result = run_command(sys.executable, "-m", "pytest", "-q", "tests/test_billing_gateway.py")
    assert result.returncode == 0, result.stdout + result.stderr
