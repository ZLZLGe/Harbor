import json
from pathlib import Path

import pandas as pd


SOURCE_FILE = Path("/root/data/pv_array_ratio.csv")
OUTPUT_FILE = Path("/root/pv_drift_report.json")


def compute_expected_report():
    df = pd.read_csv(SOURCE_FILE)
    maintenance_filtered = df.loc[df["maintenance_flag"] == 0].copy().reset_index(drop=True)

    spike_reference = maintenance_filtered["power_ratio"].rolling(
        window=21,
        center=True,
        min_periods=11,
    ).median()
    spike_mask = (maintenance_filtered["power_ratio"] - spike_reference).abs() > 0.035

    clean = maintenance_filtered.loc[~spike_mask].copy().reset_index(drop=True)
    drift_baseline = clean["power_ratio"].rolling(
        window=121,
        center=True,
        min_periods=61,
    ).median()
    drift_baseline = drift_baseline.bfill().ffill()

    clean_ratio = clean["power_ratio"] / drift_baseline
    clean_ratio = clean_ratio / clean_ratio.median()
    clean["clean_ratio"] = clean_ratio
    clean["timestamp"] = pd.to_datetime(clean["timestamp"])

    stable_mask = (clean["clean_ratio"] - 1.0).abs() <= 0.006
    best_start = None
    best_end = None
    current_start = None

    for idx, is_stable in enumerate(stable_mask.tolist()):
        if not is_stable:
            current_start = None
            continue

        if idx == 0:
            current_start = 0
        else:
            previous_time = clean.loc[idx - 1, "timestamp"]
            current_time = clean.loc[idx, "timestamp"]
            contiguous = stable_mask.iloc[idx - 1] and (current_time - previous_time).total_seconds() == 60
            if not contiguous:
                current_start = idx

        if best_start is None:
            best_start = current_start
            best_end = idx
            continue

        current_length = idx - current_start + 1
        best_length = best_end - best_start + 1
        if current_length > best_length:
            best_start = current_start
            best_end = idx

    stable_interval = clean.iloc[best_start : best_end + 1]

    return {
        "source_file": str(SOURCE_FILE),
        "removed_points": {
            "maintenance": int((df["maintenance_flag"] != 0).sum()),
            "spikes": int(spike_mask.sum()),
            "total": int((df["maintenance_flag"] != 0).sum() + spike_mask.sum()),
        },
        "cleaned_points": int(len(clean)),
        "preclean_dispersion_mad": float(
            (maintenance_filtered["power_ratio"] - maintenance_filtered["power_ratio"].median()).abs().median()
        ),
        "cleaned_dispersion_mad": float((clean["clean_ratio"] - 1.0).abs().median()),
        "cleaned_std": float(clean["clean_ratio"].std(ddof=0)),
        "stability_improvement_ratio": float(
            (maintenance_filtered["power_ratio"] - maintenance_filtered["power_ratio"].median()).abs().median()
            / (clean["clean_ratio"] - 1.0).abs().median()
        ),
        "longest_stable_generation_interval": {
            "start_timestamp": stable_interval["timestamp"].iloc[0].isoformat(),
            "end_timestamp": stable_interval["timestamp"].iloc[-1].isoformat(),
            "duration_minutes": int(len(stable_interval)),
            "n_points": int(len(stable_interval)),
            "mean_clean_ratio": float(stable_interval["clean_ratio"].mean()),
            "max_abs_deviation": float((stable_interval["clean_ratio"] - 1.0).abs().max()),
        },
    }


def load_output():
    assert OUTPUT_FILE.exists(), "缺少 /root/pv_drift_report.json"
    with OUTPUT_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def assert_close(actual, expected, tol=1e-6):
    assert abs(actual - expected) <= tol, f"数值不匹配: actual={actual}, expected={expected}, tol={tol}"


def test_output_schema_and_counts():
    output = load_output()

    assert output["source_file"] == str(SOURCE_FILE)
    assert set(output["removed_points"]) >= {"maintenance", "spikes", "total"}
    assert output["removed_points"]["total"] == (
        output["removed_points"]["maintenance"] + output["removed_points"]["spikes"]
    )
    assert output["cleaned_points"] == 600 - output["removed_points"]["total"]

    interval = output["longest_stable_generation_interval"]
    assert set(interval) >= {
        "start_timestamp",
        "end_timestamp",
        "duration_minutes",
        "n_points",
        "mean_clean_ratio",
        "max_abs_deviation",
    }
    assert interval["duration_minutes"] == interval["n_points"]


def test_report_matches_reference_pipeline():
    output = load_output()
    expected = compute_expected_report()

    assert output["removed_points"] == expected["removed_points"]
    assert output["cleaned_points"] == expected["cleaned_points"]
    assert_close(output["preclean_dispersion_mad"], expected["preclean_dispersion_mad"])
    assert_close(output["cleaned_dispersion_mad"], expected["cleaned_dispersion_mad"])
    assert_close(output["cleaned_std"], expected["cleaned_std"])
    assert_close(output["stability_improvement_ratio"], expected["stability_improvement_ratio"])

    output_interval = output["longest_stable_generation_interval"]
    expected_interval = expected["longest_stable_generation_interval"]
    assert output_interval["start_timestamp"] == expected_interval["start_timestamp"]
    assert output_interval["end_timestamp"] == expected_interval["end_timestamp"]
    assert output_interval["duration_minutes"] == expected_interval["duration_minutes"]
    assert output_interval["n_points"] == expected_interval["n_points"]
    assert_close(output_interval["mean_clean_ratio"], expected_interval["mean_clean_ratio"])
    assert_close(output_interval["max_abs_deviation"], expected_interval["max_abs_deviation"])


def test_report_reflects_clear_stability_gain():
    output = load_output()

    assert output["cleaned_dispersion_mad"] < output["preclean_dispersion_mad"]
