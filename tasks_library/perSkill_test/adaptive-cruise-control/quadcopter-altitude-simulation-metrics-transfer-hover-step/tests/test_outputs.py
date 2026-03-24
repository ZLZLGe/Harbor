import json
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path("/root")
RUNS_PATH = ROOT / "quadcopter_altitude_runs.csv"
SPEC_PATH = ROOT / "scorecard_spec.yaml"
OUTPUT_PATH = ROOT / "quadcopter_altitude_scorecard.json"


def rise_time(times, values, target):
    t10 = None
    t90 = None
    for t, v in zip(times, values):
        if t10 is None and v >= 0.1 * target:
            t10 = float(t)
        if t90 is None and v >= 0.9 * target:
            t90 = float(t)
            break
    if t10 is None or t90 is None:
        return None
    return t90 - t10


def overshoot_percent(values, target):
    maximum = max(values)
    if maximum <= target:
        return 0.0
    return ((maximum - target) / target) * 100.0


def steady_state_error(values, target, final_fraction):
    start = int(len(values) * (1.0 - final_fraction))
    final_slice = values[start:]
    final_average = sum(final_slice) / len(final_slice)
    return abs(target - final_average)


def settling_time(times, values, target, tolerance):
    band = target * tolerance
    lower = target - band
    upper = target + band
    settled_at = None
    for t, v in zip(times, values):
        if v < lower or v > upper:
            settled_at = None
        elif settled_at is None:
            settled_at = float(t)
    return settled_at


def expected_payload():
    with SPEC_PATH.open("r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)

    runs = pd.read_csv(RUNS_PATH)
    climb_spec = spec["phases"]["climb_step"]
    recovery_spec = spec["phases"]["gust_recovery"]
    limits = spec["limits"]
    normalizers = spec["score_normalizers"]
    hold_target = float(spec["targets"]["hold_altitude_m"])

    controllers = []
    for controller_id, group in runs.groupby("controller_id"):
        group = group.sort_values("time_s")
        climb = group[
            (group["time_s"] >= climb_spec["start_time_s"])
            & (group["time_s"] <= climb_spec["end_time_s"])
        ]
        recovery = group[
            (group["time_s"] >= recovery_spec["start_time_s"])
            & (group["time_s"] <= recovery_spec["end_time_s"])
        ].copy()

        recovery_origin = float(recovery.iloc[0][recovery_spec["signal_column"]])
        recovery_target = hold_target - recovery_origin
        recovery["recovery_signal_m"] = recovery[recovery_spec["signal_column"]] - recovery_origin
        recovery_times = recovery["time_s"] - recovery_spec["start_time_s"]

        climb_raw = {
            "rise_time_s": rise_time(
                climb["time_s"].tolist(),
                climb[climb_spec["signal_column"]].tolist(),
                float(climb_spec["target"]),
            ),
            "overshoot_pct": overshoot_percent(
                climb[climb_spec["signal_column"]].tolist(),
                float(climb_spec["target"]),
            ),
            "settling_time_s": settling_time(
                climb["time_s"].tolist(),
                climb[climb_spec["signal_column"]].tolist(),
                float(climb_spec["target"]),
                float(climb_spec["settling_tolerance"]),
            ),
            "steady_state_error_m": steady_state_error(
                climb[climb_spec["signal_column"]].tolist(),
                float(climb_spec["target"]),
                float(climb_spec["steady_state_fraction"]),
            ),
        }
        recovery_raw = {
            "rise_time_s": rise_time(
                recovery_times.tolist(),
                recovery["recovery_signal_m"].tolist(),
                recovery_target,
            ),
            "overshoot_pct": overshoot_percent(
                recovery["recovery_signal_m"].tolist(),
                recovery_target,
            ),
            "settling_time_s": settling_time(
                recovery_times.tolist(),
                recovery["recovery_signal_m"].tolist(),
                recovery_target,
                float(recovery_spec["settling_tolerance"]),
            ),
            "steady_state_error_m": steady_state_error(
                recovery["recovery_signal_m"].tolist(),
                recovery_target,
                float(recovery_spec["steady_state_fraction"]),
            ),
        }

        score_inputs = {
            "climb_rise_time_s": climb_raw["rise_time_s"],
            "climb_overshoot_pct": climb_raw["overshoot_pct"],
            "climb_settling_time_s": climb_raw["settling_time_s"],
            "climb_steady_state_error_m": climb_raw["steady_state_error_m"],
            "recovery_rise_time_s": recovery_raw["rise_time_s"],
            "recovery_overshoot_pct": recovery_raw["overshoot_pct"],
            "recovery_settling_time_s": recovery_raw["settling_time_s"],
            "recovery_steady_state_error_m": recovery_raw["steady_state_error_m"],
        }
        passes = all(score_inputs[key] <= float(limits[key]) for key in score_inputs)
        score = sum(score_inputs[key] / float(normalizers[key]) for key in score_inputs)

        controllers.append(
            {
                "controller_id": controller_id,
                "passes_all_limits": passes,
                "overall_score": round(score, 3),
                "climb_step": {
                    key: round(float(value), 3) for key, value in climb_raw.items()
                },
                "gust_recovery": {
                    key: round(float(value), 3) for key, value in recovery_raw.items()
                },
            }
        )

    controllers.sort(
        key=lambda row: (
            0 if row["passes_all_limits"] else 1,
            row["overall_score"],
            row["controller_id"],
        )
    )
    for index, row in enumerate(controllers, start=1):
        row["rank"] = index

    return {
        "best_controller_id": controllers[0]["controller_id"],
        "controllers": controllers,
    }


def test_input_assets_exist():
    assert RUNS_PATH.exists(), "quadcopter_altitude_runs.csv is missing"
    assert SPEC_PATH.exists(), "scorecard_spec.yaml is missing"


def test_output_exists_and_has_required_top_level_shape():
    assert OUTPUT_PATH.exists(), "quadcopter_altitude_scorecard.json is missing"
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert list(payload.keys()) == [
        "best_controller_id",
        "controllers",
        "recommendation_summary",
    ]
    assert isinstance(payload["best_controller_id"], str)
    assert isinstance(payload["controllers"], list)
    assert isinstance(payload["recommendation_summary"], str)


def test_output_metrics_and_ranking_match_expected_values():
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    expected = expected_payload()

    assert payload["best_controller_id"] == expected["best_controller_id"]
    assert [row["controller_id"] for row in payload["controllers"]] == [
        row["controller_id"] for row in expected["controllers"]
    ]

    actual_by_id = {row["controller_id"]: row for row in payload["controllers"]}
    expected_by_id = {row["controller_id"]: row for row in expected["controllers"]}

    for controller_id, expected_row in expected_by_id.items():
        actual_row = actual_by_id[controller_id]
        assert set(actual_row.keys()) == {
            "controller_id",
            "rank",
            "passes_all_limits",
            "overall_score",
            "climb_step",
            "gust_recovery",
        }
        assert actual_row["rank"] == expected_row["rank"]
        assert actual_row["passes_all_limits"] == expected_row["passes_all_limits"]
        assert abs(float(actual_row["overall_score"]) - expected_row["overall_score"]) <= 1e-3

        for phase in ["climb_step", "gust_recovery"]:
            assert set(actual_row[phase].keys()) == {
                "rise_time_s",
                "overshoot_pct",
                "settling_time_s",
                "steady_state_error_m",
            }
            for metric_name, metric_value in expected_row[phase].items():
                assert (
                    abs(float(actual_row[phase][metric_name]) - metric_value) <= 1e-3
                ), f"Mismatch for {controller_id} {phase} {metric_name}"


def test_expected_winner_and_summary_text():
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    summary = payload["recommendation_summary"]

    assert payload["best_controller_id"] == "hover_balanced"
    assert "hover_balanced" in summary
    assert "hover_smooth" in summary
    assert "hover_aggressive" in summary
    assert "lowest overall score" in summary
