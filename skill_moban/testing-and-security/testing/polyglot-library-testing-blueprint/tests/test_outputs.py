import csv
import os
from pathlib import Path


EXPECTED_HEADERS = [
    "module_id",
    "runner",
    "core_pattern",
    "mock_style",
    "advanced_track",
    "coverage_tool",
    "verification_command",
]

EXPECTED_ROWS = [
    {
        "module_id": "mod-002",
        "runner": "ctest --output-on-failure",
        "core_pattern": "GoogleTest fixture + CTest target for daemon modules",
        "mock_style": "lightweight fake collaborators",
        "advanced_track": "libFuzzer property corpus; async callback harness",
        "coverage_tool": "gcovr --xml-pretty --print-summary",
        "verification_command": "cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure",
    },
    {
        "module_id": "mod-004",
        "runner": "cargo test",
        "core_pattern": "cargo test + rstest cases for library modules",
        "mock_style": "mockall trait mocks",
        "advanced_track": "proptest strategies; criterion benchmark group; #[tokio::test] async cases",
        "coverage_tool": "cargo llvm-cov --summary-only",
        "verification_command": "cargo test",
    },
    {
        "module_id": "mod-005",
        "runner": "prove -lr t",
        "core_pattern": "Test2::V0 subtests + Test::More assertions for script modules",
        "mock_style": "table-driven fixtures with plain Perl helpers",
        "advanced_track": "",
        "coverage_tool": "cover -test",
        "verification_command": "prove -lr t",
    },
    {
        "module_id": "mod-010",
        "runner": "pytest -q",
        "core_pattern": "pytest fixtures + parametrize for service modules",
        "mock_style": "pytest-mock patching for IO boundaries",
        "advanced_track": "Hypothesis property tests; pytest-asyncio event loop cases",
        "coverage_tool": "pytest --cov --cov-report=term-missing",
        "verification_command": "pytest -q",
    },
    {
        "module_id": "mod-013",
        "runner": "./gradlew test",
        "core_pattern": "Kotest FunSpec + MockK seams for api modules",
        "mock_style": "MockK coEvery/coVerify seams",
        "advanced_track": "coroutine test dispatcher scenarios",
        "coverage_tool": "./gradlew koverHtmlReport",
        "verification_command": "./gradlew test koverVerify",
    },
    {
        "module_id": "mod-017",
        "runner": "go test ./...",
        "core_pattern": "table-driven subtests for service modules",
        "mock_style": "interface stubs for IO collaborators",
        "advanced_track": "context-aware async subtests",
        "coverage_tool": "go test ./... -coverprofile=coverage.out",
        "verification_command": "go test ./...",
    },
    {
        "module_id": "mod-021",
        "runner": "go test ./...",
        "core_pattern": "table-driven subtests for cli modules",
        "mock_style": "table-driven fixtures and in-memory fakes",
        "advanced_track": "go test fuzz targets; Benchmark* subbenchmarks",
        "coverage_tool": "go test ./... -coverprofile=coverage.out",
        "verification_command": "go test ./...",
    },
    {
        "module_id": "mod-090",
        "runner": "ctest --output-on-failure",
        "core_pattern": "GoogleTest fixture + CTest target for library modules",
        "mock_style": "GoogleMock interface mock",
        "advanced_track": "google-benchmark microbench",
        "coverage_tool": "gcovr --xml-pretty --print-summary",
        "verification_command": "cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure",
    },
]

NULL_LIKE = {"null", "none", "n/a", "nil", "na"}

REQUIRED_SKILL_DIRS = [
    "09__cpp-testing",
    "10__cpp-testing",
    "11__cpp-testing",
    "19__golang-testing",
    "20__golang-testing",
    "21__golang-testing",
    "22__golang-testing",
    "23__golang-testing",
    "24__kotlin-testing",
    "25__kotlin-testing",
    "26__kotlin-testing",
    "30__perl-testing",
    "31__perl-testing",
    "32__python-testing",
    "33__python-testing",
    "34__python-testing",
    "35__python-testing",
    "36__rust-testing",
    "37__rust-testing",
    "38__rust-testing",
]


def workspace_root() -> Path:
    root = os.environ.get("WORKSPACE_ROOT")
    if not root:
        root = str(Path(__file__).resolve().parents[1] / "workspace")
    return Path(root)


def output_path() -> Path:
    return workspace_root() / "output" / "polyglot_test_blueprint.csv"


def skills_root() -> Path:
    return Path(__file__).resolve().parents[1] / "environment" / "skills"


def read_rows():
    path = output_path()
    if not path.exists():
        raise AssertionError(f"Missing output CSV: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames
        rows = list(reader)
    return headers, rows


def test_output_matches_expected_blueprint():
    headers, rows = read_rows()
    assert headers == EXPECTED_HEADERS, f"Unexpected headers: {headers}"
    assert rows == EXPECTED_ROWS, "Output rows did not match the expected deterministic blueprint"


def test_rows_sorted_and_without_null_like_strings():
    _, rows = read_rows()
    module_ids = [row["module_id"] for row in rows]
    assert module_ids == sorted(module_ids), f"module_id values are not sorted: {module_ids}"
    for row in rows:
        for key, value in row.items():
            lowered = value.strip().lower()
            assert lowered not in NULL_LIKE, f"Field {key} contains null-like string: {value!r}"


def test_skill_directories_present():
    root = skills_root()
    assert root.exists(), f"Missing skills root: {root}"
    actual = sorted(path.name for path in root.iterdir() if path.is_dir())
    assert actual == REQUIRED_SKILL_DIRS, f"Unexpected skill directory set: {actual}"
    for name in REQUIRED_SKILL_DIRS:
        skill_file = root / name / "SKILL.md"
        assert skill_file.exists(), f"Missing copied skill file: {skill_file}"


def main():
    test_output_matches_expected_blueprint()
    test_rows_sorted_and_without_null_like_strings()
    test_skill_directories_present()


if __name__ == "__main__":
    main()
