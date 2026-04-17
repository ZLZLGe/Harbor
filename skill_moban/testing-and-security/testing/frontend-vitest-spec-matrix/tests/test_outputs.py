import csv
import os
from pathlib import Path


OUTPUT_HEADERS = [
    "target_id",
    "test_style",
    "required_scenarios",
    "mock_strategy",
    "rtl_tools",
    "coverage_goal",
    "execution_order",
]

EXPECTED_ROWS = [
    {
        "target_id": "cmp_async_panel",
        "test_style": "vitest rtl component black-box",
        "required_scenarios": "render-baseline;semantic-selectors;async-state-settling;error-boundary-or-fallback",
        "mock_strategy": "prefer real collaborators; mock external boundary only",
        "rtl_tools": "render;screen;userEvent;waitFor",
        "coverage_goal": "branch coverage for common states",
        "execution_order": "04",
    },
    {
        "target_id": "cmp_search_page",
        "test_style": "vitest rtl component black-box",
        "required_scenarios": "render-baseline;semantic-selectors;async-state-settling;url-query-sync;http-success-and-empty;error-boundary-or-fallback",
        "mock_strategy": "mock network boundary only; use real nuqs adapter",
        "rtl_tools": "render;screen;userEvent;waitFor;NuqsTestingAdapter;nock",
        "coverage_goal": "state matrix coverage including edge cases",
        "execution_order": "05",
    },
    {
        "target_id": "hook_filters",
        "test_style": "vitest rtl hook black-box",
        "required_scenarios": "invoke-baseline;observable-state-assertions;url-query-sync",
        "mock_strategy": "use real nuqs adapter; mock external boundary only",
        "rtl_tools": "renderHook;act;NuqsTestingAdapter",
        "coverage_goal": "baseline behavior coverage",
        "execution_order": "03",
    },
    {
        "target_id": "util_formatter",
        "test_style": "vitest unit black-box",
        "required_scenarios": "input-output-contract;observable-state-assertions",
        "mock_strategy": "prefer real collaborators; mock external boundary only",
        "rtl_tools": "vi.fn",
        "coverage_goal": "baseline behavior coverage",
        "execution_order": "01",
    },
    {
        "target_id": "util_retry_delay",
        "test_style": "vitest unit black-box",
        "required_scenarios": "input-output-contract;observable-state-assertions;async-state-settling;error-boundary-or-fallback",
        "mock_strategy": "prefer real collaborators; mock external boundary only",
        "rtl_tools": "vi.fn;waitFor",
        "coverage_goal": "baseline behavior coverage",
        "execution_order": "02",
    },
]

NULL_LIKE_VALUES = {"", "null", "none", "n/a", "na", "nil", "undefined"}


def main() -> None:
    workspace_root = Path(os.environ["WORKSPACE_ROOT"])
    output_path = workspace_root / "output" / "frontend_test_matrix.csv"
    assert output_path.exists(), f"Missing output file: {output_path}"

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames
        rows = list(reader)

    assert headers == OUTPUT_HEADERS, f"Expected headers {OUTPUT_HEADERS}, got {headers}"
    assert rows == EXPECTED_ROWS, "Output rows do not match expected deterministic matrix"

    target_ids = [row["target_id"] for row in rows]
    assert target_ids == sorted(target_ids), "Rows must be sorted by target_id ascending"

    for row in rows:
        assert set(row.keys()) == set(OUTPUT_HEADERS), f"Unexpected columns in row: {row}"
        for key, value in row.items():
            normalized = value.strip().lower()
            assert normalized not in NULL_LIKE_VALUES, f"Null-like value in {key}: {value!r}"
            assert value == value.strip(), f"Unexpected surrounding whitespace in {key}: {value!r}"


if __name__ == "__main__":
    main()
