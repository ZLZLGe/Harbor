#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
INPUT_CSV="${WORKSPACE_ROOT}/input/modules.csv"
OUTPUT_DIR="${WORKSPACE_ROOT}/output"
OUTPUT_CSV="${OUTPUT_DIR}/polyglot_test_blueprint.csv"

mkdir -p "${OUTPUT_DIR}"

INPUT_CSV="${INPUT_CSV}" OUTPUT_CSV="${OUTPUT_CSV}" python3 - <<'PY'
import csv
import os
from pathlib import Path


INPUT_CSV = Path(os.environ["INPUT_CSV"])
OUTPUT_CSV = Path(os.environ["OUTPUT_CSV"])

OUTPUT_HEADERS = [
    "module_id",
    "runner",
    "core_pattern",
    "mock_style",
    "advanced_track",
    "coverage_tool",
    "verification_command",
]


def parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "y"}


def join_tracks(parts):
    return "; ".join(part for part in parts if part)


def cpp_mapping(module_kind, needs_io_mock, needs_property_tests, needs_benchmarks, needs_async):
    return {
        "runner": "ctest --output-on-failure",
        "core_pattern": f"GoogleTest fixture + CTest target for {module_kind} modules",
        "mock_style": "GoogleMock interface mock" if needs_io_mock else "lightweight fake collaborators",
        "advanced_track": join_tracks([
            "libFuzzer property corpus" if needs_property_tests else "",
            "google-benchmark microbench" if needs_benchmarks else "",
            "async callback harness" if needs_async else "",
        ]),
        "coverage_tool": "gcovr --xml-pretty --print-summary",
        "verification_command": "cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure",
    }


def go_mapping(module_kind, needs_io_mock, needs_property_tests, needs_benchmarks, needs_async):
    return {
        "runner": "go test ./...",
        "core_pattern": f"table-driven subtests for {module_kind} modules",
        "mock_style": "interface stubs for IO collaborators" if needs_io_mock else "table-driven fixtures and in-memory fakes",
        "advanced_track": join_tracks([
            "go test fuzz targets" if needs_property_tests else "",
            "Benchmark* subbenchmarks" if needs_benchmarks else "",
            "context-aware async subtests" if needs_async else "",
        ]),
        "coverage_tool": "go test ./... -coverprofile=coverage.out",
        "verification_command": "go test ./...",
    }


def kotlin_mapping(module_kind, needs_io_mock, needs_property_tests, needs_benchmarks, needs_async):
    return {
        "runner": "./gradlew test",
        "core_pattern": f"Kotest FunSpec + MockK seams for {module_kind} modules",
        "mock_style": "MockK coEvery/coVerify seams" if needs_io_mock else "Kotest fixtures with lightweight fakes",
        "advanced_track": join_tracks([
            "Kotest property checks" if needs_property_tests else "",
            "kotlinx-benchmark suite" if needs_benchmarks else "",
            "coroutine test dispatcher scenarios" if needs_async else "",
        ]),
        "coverage_tool": "./gradlew koverHtmlReport",
        "verification_command": "./gradlew test koverVerify",
    }


def perl_mapping(module_kind, needs_io_mock, needs_property_tests, needs_benchmarks, needs_async):
    return {
        "runner": "prove -lr t",
        "core_pattern": f"Test2::V0 subtests + Test::More assertions for {module_kind} modules",
        "mock_style": "Test2::Mock + local overrides" if needs_io_mock else "table-driven fixtures with plain Perl helpers",
        "advanced_track": join_tracks([
            "generator-style edge subtests" if needs_property_tests else "",
            "Benchmark.pm smoke checks" if needs_benchmarks else "",
            "Future::AsyncAwait harness" if needs_async else "",
        ]),
        "coverage_tool": "cover -test",
        "verification_command": "prove -lr t",
    }


def python_mapping(module_kind, needs_io_mock, needs_property_tests, needs_benchmarks, needs_async):
    return {
        "runner": "pytest -q",
        "core_pattern": f"pytest fixtures + parametrize for {module_kind} modules",
        "mock_style": "pytest-mock patching for IO boundaries" if needs_io_mock else "fixture-backed fakes",
        "advanced_track": join_tracks([
            "Hypothesis property tests" if needs_property_tests else "",
            "pytest-benchmark cases" if needs_benchmarks else "",
            "pytest-asyncio event loop cases" if needs_async else "",
        ]),
        "coverage_tool": "pytest --cov --cov-report=term-missing",
        "verification_command": "pytest -q",
    }


def rust_mapping(module_kind, needs_io_mock, needs_property_tests, needs_benchmarks, needs_async):
    return {
        "runner": "cargo test",
        "core_pattern": f"cargo test + rstest cases for {module_kind} modules",
        "mock_style": "mockall trait mocks" if needs_io_mock else "in-memory test doubles",
        "advanced_track": join_tracks([
            "proptest strategies" if needs_property_tests else "",
            "criterion benchmark group" if needs_benchmarks else "",
            "#[tokio::test] async cases" if needs_async else "",
        ]),
        "coverage_tool": "cargo llvm-cov --summary-only",
        "verification_command": "cargo test",
    }


LANGUAGE_MAP = {
    "cpp": cpp_mapping,
    "c++": cpp_mapping,
    "go": go_mapping,
    "golang": go_mapping,
    "kotlin": kotlin_mapping,
    "perl": perl_mapping,
    "python": python_mapping,
    "rust": rust_mapping,
}


with INPUT_CSV.open("r", encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)
    rows = list(reader)

output_rows = []
for row in rows:
    language = row["language"].strip().lower()
    if language not in LANGUAGE_MAP:
        raise ValueError(f"Unsupported language: {row['language']}")

    module_kind = row["module_kind"].strip().lower()
    mapped = LANGUAGE_MAP[language](
        module_kind,
        parse_bool(row["needs_io_mock"]),
        parse_bool(row["needs_property_tests"]),
        parse_bool(row["needs_benchmarks"]),
        parse_bool(row["needs_async"]),
    )
    output_rows.append({
        "module_id": row["module_id"].strip(),
        **mapped,
    })

output_rows.sort(key=lambda item: item["module_id"])

with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS)
    writer.writeheader()
    writer.writerows(output_rows)
PY
