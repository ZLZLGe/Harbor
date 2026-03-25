import ast
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(
    os.environ.get("TASK_PROJECT_ROOT", "/workspace/dispatch-board")
).resolve()
TEST_FILE = PROJECT_ROOT / "tests" / "test_dispatch_contract.py"
REPORT_PATH = PROJECT_ROOT / "notes" / "async_contract_report.md"

REQUIRED_IMPORTED_SYMBOLS = [
    "DispatchBoardService",
    "InMemoryDispatchClient",
    "ServiceContractError",
]

REQUIRED_METHOD_NAMES = [
    "get_service_info",
    "call_tool",
    "run_batch",
]

REQUIRED_TOOL_NAMES = [
    "lookup_ticket",
    "list_escalations",
    "schedule_callback",
    "close_ticket",
]

FORBIDDEN_SOURCE_TOKENS = [
    "http://",
    "https://",
    "127.0.0.1",
    "localhost",
    "RemoteDispatchClient",
    "requests",
    "httpx",
    "subprocess",
    "asyncio.sleep",
]


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


def is_pytest_raises_call(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "pytest"
        and node.func.attr == "raises"
    ):
        return False
    return bool(node.args) and isinstance(node.args[0], ast.Name) and node.args[0].id == "ServiceContractError"


def test_authored_test_file_has_required_async_structure():
    assert TEST_FILE.exists(), "缺少 tests/test_dispatch_contract.py"

    source = TEST_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    async_test_count = 0
    fixture_count = 0
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("test_"):
            async_test_count += 1
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            is_fixture_decorator(decorator) for decorator in node.decorator_list
        ):
            fixture_count += 1

    assert async_test_count >= 4, "至少需要 4 个 async pytest 测试"
    assert fixture_count >= 1, "至少需要 1 个 pytest fixture"


def test_authored_test_file_matches_required_contract_focus():
    source = TEST_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    string_constants = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert_count = sum(isinstance(node, ast.Assert) for node in ast.walk(tree))
    raises_count = sum(
        any(is_pytest_raises_call(item.context_expr) for item in node.items)
        for node in ast.walk(tree)
        if isinstance(node, (ast.With, ast.AsyncWith))
    )

    for token in REQUIRED_IMPORTED_SYMBOLS:
        assert token in names, f"测试文件里缺少关键契约符号: {token}"

    for token in REQUIRED_METHOD_NAMES:
        assert token in attrs, f"测试文件里缺少关键接口调用: {token}"

    for token in REQUIRED_TOOL_NAMES:
        assert token in string_constants, f"测试文件里缺少关键工具场景: {token}"

    assert assert_count >= 6, "测试文件里的断言数量不足，无法证明契约覆盖"
    assert raises_count >= 1, "至少需要 1 个 pytest.raises(ServiceContractError) 失败场景"

    for token in FORBIDDEN_SOURCE_TOKENS:
        assert token not in source, f"测试文件里不应出现: {token}"


def test_report_file_matches_contract():
    assert REPORT_PATH.exists(), "缺少 notes/async_contract_report.md"

    content = REPORT_PATH.read_text(encoding="utf-8").strip()
    assert content.startswith("# Async Contract Report")
    assert "不依赖真实网络" in content or "没有真实网络" in content

    table_lines = [line for line in content.splitlines() if line.startswith("|")]
    assert table_lines, "报告里缺少 Markdown 表格"
    assert (
        table_lines[0].strip() == "| interface | scenario | asserted_contract |"
    ), "报告表头不符合要求"
    assert len(table_lines[2:]) >= 4, "报告表格至少需要 4 行数据"

    required_report_token_groups = [
        ("get_service_info",),
        ("lookup_ticket", "INC-42"),
        ("run_batch",),
        ("close_ticket", "ServiceContractError"),
        ("queued",),
    ]
    for token_group in required_report_token_groups:
        assert any(token in content for token in token_group), (
            "报告里缺少以下关键信息之一: " + " / ".join(token_group)
        )


def test_authored_tests_collect_expected_cases():
    result = run_command(
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "tests/test_dispatch_contract.py",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    collected = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("tests/test_dispatch_contract.py::")
    ]
    assert len(collected) >= 4, result.stdout


def test_authored_tests_pass():
    result = run_command(sys.executable, "-m", "pytest", "-q", "tests/test_dispatch_contract.py")
    assert result.returncode == 0, result.stdout + result.stderr
