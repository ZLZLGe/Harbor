from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_CSV = Path("/root/icequake_candidates.csv")
METHOD_TXT = Path("/root/icequake_method.txt")
REFERENCE_CSV = Path("/tests/reference_icequakes.csv")
MAINTENANCE_CSV = Path("/root/data/maintenance_windows.csv")
TIME_TOLERANCE = 3.5


def load_times(path: Path, column: str = "time") -> pd.DataFrame:
    frame = pd.read_csv(path)
    assert column in frame.columns, f"{path} is missing the required '{column}' column"
    frame[column] = frame[column].map(datetime.fromisoformat)
    return frame


def to_epoch_seconds(values: pd.Series) -> np.ndarray:
    epoch = datetime(2019, 1, 1)
    return np.array([(value.replace(tzinfo=None) - epoch).total_seconds() for value in values])


def detection_scores(predicted: np.ndarray, reference: np.ndarray, tolerance: float) -> tuple[float, float, float]:
    matches = np.abs(predicted[np.newaxis, :] - reference[:, np.newaxis]) <= tolerance
    recalled = np.sum(matches, axis=1) > 0
    detected = np.sum(matches, axis=0) > 0
    recall = float(np.sum(recalled) / len(reference))
    precision = float(np.sum(detected) / len(predicted))
    f1 = 2 * recall * precision / (recall + precision)
    return recall, precision, f1


def test_method_note_prefers_generalizable_mixed_sensor_picker():
    assert METHOD_TXT.exists(), "Expected /root/icequake_method.txt to be created"
    note = METHOD_TXT.read_text(encoding="utf-8").lower()
    required_keywords = ["deep", "mixed", "template", "sta/lta"]
    assert all(keyword in note for keyword in required_keywords), note


def test_candidate_schema_and_maintenance_exclusion():
    assert OUTPUT_CSV.exists(), "Expected /root/icequake_candidates.csv to be created"
    candidates = load_times(OUTPUT_CSV)
    maintenance = load_times(MAINTENANCE_CSV, column="window_start")
    maintenance["window_end"] = maintenance["window_end"].map(datetime.fromisoformat)

    required_columns = {
        "approach_family",
        "support_stations",
        "sensor_class_count",
        "sensor_types",
        "median_pick_probability",
        "network_coherence",
    }
    assert required_columns.issubset(candidates.columns), candidates.columns
    assert candidates["time"].is_monotonic_increasing, "Candidate times must be sorted in ascending order"
    assert candidates["time"].is_unique, "Candidate times should not contain exact duplicates"
    assert 9 <= len(candidates) <= 12, f"Unexpected candidate count: {len(candidates)}"
    assert set(candidates["approach_family"]) == {"deep_picker_association"}, candidates["approach_family"].tolist()
    assert (candidates["support_stations"] >= 3).all(), "Each candidate must have support from at least three stations"
    assert (candidates["sensor_class_count"] >= 2).all(), "Each candidate must span at least two sensor classes"
    assert (candidates["median_pick_probability"] >= 0.75).all(), "Each candidate must have strong picker confidence"
    assert (candidates["network_coherence"] >= 0.70).all(), "Each candidate must be coherent across the sparse network"

    for _, window in maintenance.iterrows():
        inside_window = candidates["time"].between(window["window_start"], window["window_end"])
        assert not inside_window.any(), f"Found candidate inside maintenance window: {window.to_dict()}"


def test_reference_icequake_schedule_recovery():
    candidates = load_times(OUTPUT_CSV)
    reference = load_times(REFERENCE_CSV)

    predicted = to_epoch_seconds(candidates["time"])
    expected = to_epoch_seconds(reference["time"])
    recall, precision, f1 = detection_scores(predicted, expected, TIME_TOLERANCE)

    print(f"Recall: {recall:.3f}")
    print(f"Precision: {precision:.3f}")
    print(f"F1: {f1:.3f}")

    assert recall >= 0.90, f"Recall too low: {recall:.3f}"
    assert precision >= 0.90, f"Precision too low: {precision:.3f}"
    assert f1 >= 0.90, f"F1 too low: {f1:.3f}"
