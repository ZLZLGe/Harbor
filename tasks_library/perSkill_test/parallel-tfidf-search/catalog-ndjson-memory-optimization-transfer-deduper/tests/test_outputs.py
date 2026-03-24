#!/usr/bin/env python3

from __future__ import annotations

import gc
import importlib.util
import json
import sys
import tracemalloc
from pathlib import Path

import pytest

sys.path.insert(0, "/root/workspace")

from catalog_baseline import (
    dedupe_catalog_baseline,
    write_canonical_catalog_baseline,
)
from catalog_common import (
    CatalogBuildResult,
    CanonicalCatalogRecord,
    canonical_record_to_dict,
)
from catalog_factory import write_catalog_ndjson


WORKSPACE = Path("/root/workspace")
FIXTURE_CATALOG = WORKSPACE / "catalog_fixture.ndjson"
EXPECTED_RECORDS = WORKSPACE / "expected_catalog_records.json"
EXPECTED_OUTPUT = WORKSPACE / "expected_catalog_output.ndjson"
SOLUTION_PATH = WORKSPACE / "catalog_deduper_solution.py"


def load_solution():
    if not SOLUTION_PATH.exists():
        pytest.fail("missing /root/workspace/catalog_deduper_solution.py")

    spec = importlib.util.spec_from_file_location("catalog_deduper_solution", SOLUTION_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["catalog_deduper_solution"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def solution():
    return load_solution()


def normalize_records(result: CatalogBuildResult):
    return [canonical_record_to_dict(record) for record in result.records]


def measure_peak_bytes(func, *args, **kwargs):
    gc.collect()
    tracemalloc.start()
    try:
        result = func(*args, **kwargs)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, peak


class TestSolutionShape:
    def test_module_exports_required_functions(self, solution):
        assert hasattr(solution, "dedupe_catalog")
        assert hasattr(solution, "write_canonical_catalog")


class TestFixtureBehavior:
    def test_fixture_matches_expected_records_and_output(self, solution, tmp_path):
        result = solution.dedupe_catalog(FIXTURE_CATALOG)
        assert isinstance(result, CatalogBuildResult)
        assert all(isinstance(record, CanonicalCatalogRecord) for record in result.records)
        assert result.input_count == 8
        assert result.canonical_count == 4
        assert result.duplicate_count == 4

        expected_records = json.loads(EXPECTED_RECORDS.read_text(encoding="utf-8"))
        assert normalize_records(result) == expected_records

        output_path = tmp_path / "fixture-output.ndjson"
        written_result = solution.write_canonical_catalog(FIXTURE_CATALOG, output_path)
        assert normalize_records(written_result) == expected_records
        assert output_path.read_text(encoding="utf-8") == EXPECTED_OUTPUT.read_text(encoding="utf-8")


class TestGeneratedCatalogs:
    @pytest.mark.parametrize(
        ("num_products", "duplicates_per_product", "seed"),
        [
            (30, 4, 11),
            (80, 7, 29),
            (140, 9, 71),
        ],
    )
    def test_generated_catalog_matches_baseline(
        self,
        solution,
        tmp_path,
        num_products,
        duplicates_per_product,
        seed,
    ):
        catalog_path = tmp_path / f"generated-{seed}.ndjson"
        row_count = write_catalog_ndjson(
            catalog_path,
            num_products=num_products,
            duplicates_per_product=duplicates_per_product,
            seed=seed,
        )
        assert row_count == num_products * duplicates_per_product

        baseline = dedupe_catalog_baseline(catalog_path)
        observed = solution.dedupe_catalog(catalog_path)

        assert observed.input_count == baseline.input_count == row_count
        assert observed.canonical_count == baseline.canonical_count == num_products
        assert normalize_records(observed) == normalize_records(baseline)

        expected_output_path = tmp_path / "baseline-output.ndjson"
        observed_output_path = tmp_path / "observed-output.ndjson"
        write_canonical_catalog_baseline(catalog_path, expected_output_path)
        solution.write_canonical_catalog(catalog_path, observed_output_path)
        assert observed_output_path.read_text(encoding="utf-8") == expected_output_path.read_text(encoding="utf-8")


class TestMemoryBudget:
    def test_peak_memory_is_far_below_baseline(self, solution, tmp_path):
        catalog_path = tmp_path / "large-catalog.ndjson"
        row_count = write_catalog_ndjson(
            catalog_path,
            num_products=2500,
            duplicates_per_product=10,
            seed=404,
        )
        assert row_count == 25000

        baseline_result, baseline_peak = measure_peak_bytes(dedupe_catalog_baseline, catalog_path)
        observed_result, observed_peak = measure_peak_bytes(solution.dedupe_catalog, catalog_path)

        assert normalize_records(observed_result) == normalize_records(baseline_result)
        assert observed_peak < baseline_peak * 0.2, (
            f"candidate peak {observed_peak} not below 20% of baseline peak {baseline_peak}"
        )
        assert observed_peak < 20 * 1024 * 1024, (
            f"candidate peak too high: {observed_peak} bytes"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
