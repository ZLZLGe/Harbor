import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

OUTPUT_FILE = Path("/root/frame_sync_results.csv")
PREAMBLE_FILE = Path("/root/data/preamble_catalog.json")
SEGMENTS_FILE = Path("/root/data/received_segments.json")
SCORE_TOLERANCE = 1e-5


def to_complex_array(pairs):
    return np.array([complex(i, q) for i, q in pairs], dtype=np.complex128)


def load_expected_rows():
    catalog = json.loads(PREAMBLE_FILE.read_text())
    segments_doc = json.loads(SEGMENTS_FILE.read_text())

    preambles = {
        item["preamble_id"]: to_complex_array(item["samples"])
        for item in catalog["preambles"]
    }

    rows = []
    for segment in sorted(segments_doc["segments"], key=lambda item: item["segment_id"]):
        samples = to_complex_array(segment["samples"])
        best = None

        for preamble_id, template in preambles.items():
            limit = len(samples) - len(template) + 1
            scores = np.empty(limit, dtype=np.float64)
            for k in range(limit):
                scores[k] = abs(np.vdot(template, samples[k : k + len(template)]))

            start_index = int(scores.argmax())
            peak_score = float(scores[start_index])
            candidate = {
                "segment_id": segment["segment_id"],
                "preamble_id": preamble_id,
                "start_index": start_index,
                "peak_score": peak_score,
            }

            if best is None:
                best = candidate
                continue

            if candidate["peak_score"] > best["peak_score"]:
                best = candidate
            elif candidate["peak_score"] == best["peak_score"]:
                if candidate["preamble_id"] < best["preamble_id"] or (
                    candidate["preamble_id"] == best["preamble_id"]
                    and candidate["start_index"] < best["start_index"]
                ):
                    best = candidate

        rows.append(best)

    return rows, set(preambles), [item["segment_id"] for item in sorted(segments_doc["segments"], key=lambda item: item["segment_id"])]


@pytest.fixture(scope="module")
def agent_output():
    assert OUTPUT_FILE.exists(), f"输出文件不存在: {OUTPUT_FILE}"
    return pd.read_csv(OUTPUT_FILE)


@pytest.fixture(scope="module")
def expected():
    return load_expected_rows()


def test_columns(agent_output):
    assert list(agent_output.columns) == [
        "segment_id",
        "preamble_id",
        "start_index",
        "peak_score",
    ]


def test_row_count_and_sorting(agent_output, expected):
    _, _, ordered_segments = expected
    assert len(agent_output) == len(ordered_segments)
    assert agent_output["segment_id"].tolist() == ordered_segments


def test_basic_value_constraints(agent_output, expected):
    _, preamble_ids, ordered_segments = expected

    assert set(agent_output["segment_id"]) == set(ordered_segments)
    assert agent_output["segment_id"].is_unique
    assert set(agent_output["preamble_id"]).issubset(preamble_ids)

    start_index_numeric = pd.to_numeric(agent_output["start_index"], errors="raise")
    peak_score_numeric = pd.to_numeric(agent_output["peak_score"], errors="raise")

    assert np.all(np.isfinite(start_index_numeric))
    assert np.all(np.isfinite(peak_score_numeric))
    assert np.all(start_index_numeric >= 0)
    assert np.all(np.equal(start_index_numeric, np.floor(start_index_numeric)))
    assert np.all(peak_score_numeric > 0)


def test_matches_expected_sync_result(agent_output, expected):
    expected_rows, _, _ = expected
    expected_by_segment = {row["segment_id"]: row for row in expected_rows}

    for _, actual in agent_output.iterrows():
        segment_id = actual["segment_id"]
        expected_row = expected_by_segment[segment_id]

        assert actual["preamble_id"] == expected_row["preamble_id"]
        assert int(actual["start_index"]) == expected_row["start_index"]
        assert abs(float(actual["peak_score"]) - expected_row["peak_score"]) <= SCORE_TOLERANCE
