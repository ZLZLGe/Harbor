import csv
import os


def test_outputs() -> None:
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
    output_path = os.path.join(workspace_root, "output", "vscode_test_selection.csv")
    assert os.path.exists(output_path), f"缺少输出文件: {output_path}"

    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        actual = list(reader)
        headers = reader.fieldnames

    expected_headers = [
        "request_id",
        "script",
        "arguments",
        "scope",
        "compile_required",
        "notes",
    ]
    assert headers == expected_headers, f"输出列不匹配: {headers}"

    for row in actual:
        assert set(row) == set(expected_headers), f"输出存在额外列: {row}"
        for key, value in row.items():
            assert value != "", f"{key} 不允许为空字符串: {row}"
            assert value not in {"null", "None", "nan", "NaN"}, f"{key} 出现空值样式文本: {row}"

    expected = [
        {
            "request_id": "101",
            "script": "./scripts/test.sh",
            "arguments": 'src/vs/editor/test/common/model.test.ts --grep "should split lines" --coverage',
            "scope": "unit",
            "compile_required": "true",
            "notes": "Unit request uses scripts/test.sh semantics with the source file path and coverage enabled.",
        },
        {
            "request_id": "102",
            "script": "./scripts/test.sh",
            "arguments": '--runGlob "**/search/**/*.test.js" --grep "SearchProvider"',
            "scope": "unit",
            "compile_required": "true",
            "notes": "Unit request uses a compiled-test glob and grep filter.",
        },
        {
            "request_id": "103",
            "script": "./scripts/test-integration.sh",
            "arguments": '--run src/vs/workbench/services/search/test/browser/search.integrationTest.ts --grep "TextSearchProvider"',
            "scope": "integration-node",
            "compile_required": "true",
            "notes": "Run targets node integration tests only; extension host suites are skipped by --run.",
        },
        {
            "request_id": "104",
            "script": "./scripts/test-integration.sh",
            "arguments": '--suite "git"',
            "scope": "integration-extension",
            "compile_required": "true",
            "notes": "Suite selection targets extension host tests only; integration coverage is ignored.",
        },
        {
            "request_id": "105",
            "script": ".\\scripts\\test-integration.bat",
            "arguments": '--grep "SearchProvider"',
            "scope": "integration-all",
            "compile_required": "true",
            "notes": "Grep-only integration requests run both node integration tests and extension host suites.",
        },
        {
            "request_id": "106",
            "script": "./scripts/test-integration.sh",
            "arguments": '--runGlob "**/workbench/**/*.integrationTest.js"',
            "scope": "integration-node",
            "compile_required": "true",
            "notes": "Run glob narrows execution to node integration test files only.",
        },
        {
            "request_id": "107",
            "script": ".\\scripts\\test.bat",
            "arguments": "src/vs/workbench/test/browser/workbench.test.ts",
            "scope": "unit",
            "compile_required": "true",
            "notes": "Suite filter is ignored for unit tests; the unit source file path remains the selector.",
        },
    ]
    assert actual == expected, f"输出内容不匹配.\nactual={actual}\nexpected={expected}"


if __name__ == "__main__":
    test_outputs()
