from datetime import datetime
from pathlib import Path

import pandas as pd

MATCH_TOLERANCE_S = 1.5
MIN_PRECISION = 0.90
MIN_RECALL = 0.90


def parse_times(series: pd.Series) -> list[datetime]:
    parsed = [datetime.fromisoformat(value) for value in series]
    assert all(item.tzinfo is None for item in parsed), "time values must not include timezone information"
    return parsed


def greedy_match(predicted: list[datetime], reference: list[datetime], tolerance_s: float) -> int:
    used_predictions = set()
    matches = 0
    for truth in reference:
        best_idx = None
        best_gap = None
        for idx, guess in enumerate(predicted):
            if idx in used_predictions:
                continue
            gap = abs((guess - truth).total_seconds())
            if gap <= tolerance_s and (best_gap is None or gap < best_gap):
                best_idx = idx
                best_gap = gap
        if best_idx is not None:
            used_predictions.add(best_idx)
            matches += 1
    return matches


def test_output_contract_and_event_recovery():
    output_path = Path("/root/associated_events.csv")
    assert output_path.exists(), "missing /root/associated_events.csv"

    result = pd.read_csv(output_path)
    required_columns = {"time", "station_count", "phase_count"}
    assert required_columns.issubset(result.columns), "output must contain time, station_count, and phase_count"
    assert not result.empty, "output must contain at least one event"

    parsed_times = parse_times(result["time"])
    assert parsed_times == sorted(parsed_times), "events must be sorted by time ascending"
    assert len(set(parsed_times)) == len(parsed_times), "event times must be unique"
    assert (result["station_count"] >= 3).all(), "every event must have support from at least 3 stations"
    assert (result["phase_count"] >= 4).all(), "every event must have at least 4 supporting picks"

    reference = pd.read_csv("/tests/reference_catalog.csv")
    reference_times = parse_times(reference["time"])

    matches = greedy_match(parsed_times, reference_times, MATCH_TOLERANCE_S)
    precision = matches / len(parsed_times)
    recall = matches / len(reference_times)

    print(f"matches={matches} predicted={len(parsed_times)} reference={len(reference_times)}")
    print(f"precision={precision:.3f} recall={recall:.3f}")

    assert precision >= MIN_PRECISION, f"precision {precision:.3f} is below {MIN_PRECISION:.2f}"
    assert recall >= MIN_RECALL, f"recall {recall:.3f} is below {MIN_RECALL:.2f}"
