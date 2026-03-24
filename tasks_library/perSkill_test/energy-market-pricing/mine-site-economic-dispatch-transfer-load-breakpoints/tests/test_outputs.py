import csv
import json
import os
from pathlib import Path

import pytest

TOL = 1e-2


def resolve_existing_path(*candidates):
    for candidate in candidates:
        path = Path(candidate)
        try:
            if path.exists():
                return path
        except PermissionError:
            continue
    raise FileNotFoundError(f"None of these paths exist: {candidates}")


OUTPUT_FILE = resolve_existing_path(
    "/root/breakpoint_study.json",
    "breakpoint_study.json",
)
UNITS_FILE = resolve_existing_path(
    "/root/thermal_units.csv",
    "environment/thermal_units.csv",
)
BLOCKS_FILE = resolve_existing_path(
    "/root/load_blocks.csv",
    "environment/load_blocks.csv",
)
CONFIG_FILE = resolve_existing_path(
    "/root/study_config.json",
    "environment/study_config.json",
)


def round2(value):
    return round(float(value), 2)


def read_units(path):
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    units = []
    for row in rows:
        units.append(
            {
                "unit_id": row["unit_id"],
                "pmin_mw": float(row["pmin_mw"]),
                "pmax_mw": float(row["pmax_mw"]),
                "cost_quadratic": float(row["cost_quadratic"]),
                "cost_linear": float(row["cost_linear"]),
                "cost_fixed": float(row["cost_fixed"]),
            }
        )
    return units


def read_blocks(path):
    with path.open(encoding="utf-8") as fh:
        return [
            {"block_id": row["block_id"], "load_mw": float(row["load_mw"])}
            for row in csv.DictReader(fh)
        ]


def generator_output(unit, lambda_value):
    unconstrained = (
        lambda_value - unit["cost_linear"]
    ) / (2.0 * unit["cost_quadratic"])
    return max(unit["pmin_mw"], min(unit["pmax_mw"], unconstrained))


def solve_dispatch(units, load_mw):
    min_feasible = sum(unit["pmin_mw"] for unit in units)
    max_feasible = sum(unit["pmax_mw"] for unit in units)
    assert min_feasible - 1e-9 <= load_mw <= max_feasible + 1e-9

    low = min(
        2.0 * unit["cost_quadratic"] * unit["pmin_mw"] + unit["cost_linear"]
        for unit in units
    ) - 100.0
    high = max(
        2.0 * unit["cost_quadratic"] * unit["pmax_mw"] + unit["cost_linear"]
        for unit in units
    ) + 100.0

    for _ in range(250):
        midpoint = (low + high) / 2.0
        total_output = sum(generator_output(unit, midpoint) for unit in units)
        if total_output < load_mw:
            low = midpoint
        else:
            high = midpoint

    outputs = [generator_output(unit, (low + high) / 2.0) for unit in units]
    total_cost = sum(
        unit["cost_quadratic"] * output * output
        + unit["cost_linear"] * output
        + unit["cost_fixed"]
        for unit, output in zip(units, outputs)
    )
    return outputs, total_cost


def build_expected_report(units, blocks, config):
    report = {"load_blocks": []}
    breakpoint = None

    for block in blocks:
        outputs, total_cost = solve_dispatch(units, block["load_mw"])
        _, cost_plus_one = solve_dispatch(units, block["load_mw"] + 1.0)
        block_dispatch = [
            {"unit_id": unit["unit_id"], "output_mw": round2(output)}
            for unit, output in zip(units, outputs)
        ]
        report["load_blocks"].append(
            {
                "block_id": block["block_id"],
                "load_mw": round2(block["load_mw"]),
                "total_cost_dollars_per_hour": round2(total_cost),
                "marginal_system_cost_dollars_per_mwh": round2(
                    cost_plus_one - total_cost
                ),
                "dispatch": block_dispatch,
            }
        )

        standby_output = next(
            output
            for unit, output in zip(units, outputs)
            if unit["unit_id"] == config["standby_unit_id"]
        )
        if (
            breakpoint is None
            and standby_output > config["dispatch_threshold_mw"]
        ):
            breakpoint = {
                "unit_id": config["standby_unit_id"],
                "threshold_mw": round2(config["dispatch_threshold_mw"]),
                "first_block_id": block["block_id"],
                "first_load_mw": round2(block["load_mw"]),
                "dispatch_mw": round2(standby_output),
            }

    assert breakpoint is not None
    report["standby_breakpoint"] = breakpoint
    return report


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_FILE), f"{OUTPUT_FILE} does not exist"
    with OUTPUT_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def units():
    return read_units(UNITS_FILE)


@pytest.fixture(scope="module")
def blocks():
    return read_blocks(BLOCKS_FILE)


@pytest.fixture(scope="module")
def config():
    with CONFIG_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def expected(units, blocks, config):
    return build_expected_report(units, blocks, config)


def assert_close(actual, expected):
    assert actual == pytest.approx(expected, abs=TOL)


class TestSchema:
    def test_top_level_structure(self, report):
        assert set(report.keys()) == {"load_blocks", "standby_breakpoint"}

    def test_block_structure(self, report, units, blocks):
        expected_units = [unit["unit_id"] for unit in units]
        expected_blocks = [block["block_id"] for block in blocks]

        load_blocks = report["load_blocks"]
        assert isinstance(load_blocks, list)
        assert [block["block_id"] for block in load_blocks] == expected_blocks

        for block in load_blocks:
            assert set(block.keys()) == {
                "block_id",
                "load_mw",
                "total_cost_dollars_per_hour",
                "marginal_system_cost_dollars_per_mwh",
                "dispatch",
            }
            assert [row["unit_id"] for row in block["dispatch"]] == expected_units
            for row in block["dispatch"]:
                assert set(row.keys()) == {"unit_id", "output_mw"}

    def test_breakpoint_structure(self, report):
        assert set(report["standby_breakpoint"].keys()) == {
            "unit_id",
            "threshold_mw",
            "first_block_id",
            "first_load_mw",
            "dispatch_mw",
        }


class TestExactValues:
    def test_full_report_matches_expected(self, report, expected):
        assert report["load_blocks"] == expected["load_blocks"]
        assert report["standby_breakpoint"] == expected["standby_breakpoint"]


class TestConsistency:
    def test_dispatch_sums_match_block_loads(self, report):
        for block in report["load_blocks"]:
            total_output = sum(row["output_mw"] for row in block["dispatch"])
            assert_close(total_output, block["load_mw"])

    def test_breakpoint_is_first_threshold_crossing(self, report, config):
        threshold = config["dispatch_threshold_mw"]
        standby_unit_id = config["standby_unit_id"]
        seen_above = []
        for block in report["load_blocks"]:
            standby_output = next(
                row["output_mw"]
                for row in block["dispatch"]
                if row["unit_id"] == standby_unit_id
            )
            if standby_output > threshold:
                seen_above.append((block["block_id"], block["load_mw"], standby_output))

        assert seen_above, "Expected at least one threshold crossing"
        first_block_id, first_load_mw, first_output = seen_above[0]
        breakpoint = report["standby_breakpoint"]
        assert breakpoint["first_block_id"] == first_block_id
        assert_close(breakpoint["first_load_mw"], first_load_mw)
        assert_close(breakpoint["dispatch_mw"], first_output)

    def test_marginal_costs_non_decreasing(self, report):
        marginals = [
            block["marginal_system_cost_dollars_per_mwh"]
            for block in report["load_blocks"]
        ]
        assert marginals == sorted(marginals)
