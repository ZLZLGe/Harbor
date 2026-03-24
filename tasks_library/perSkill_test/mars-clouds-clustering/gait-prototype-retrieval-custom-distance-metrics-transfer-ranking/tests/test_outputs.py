from pathlib import Path
import os

import pandas as pd


RESULT_PATH = Path(os.environ.get("RESULT_PATH", "/root/gait_protocol_rankings.csv"))
EXPECTED_ROWS = [
    ("PAT_001", 1, "PROTO_BALANCE", "balance", 0.03850, "stability_priority", 1.00000),
    ("PAT_001", 2, "PROTO_STEADY", "steadying", 0.06762, "stability_priority", 1.00000),
    ("PAT_001", 3, "PROTO_STIFF", "knee-mobility", 0.18503, "stability_priority", 1.00000),
    ("PAT_002", 1, "PROTO_DRAG", "toe-clearance", 0.04176, "stability_priority", 1.00000),
    ("PAT_002", 2, "PROTO_FATIGUE", "endurance", 0.08196, "stability_priority", 1.00000),
    ("PAT_002", 3, "PROTO_BALANCE", "balance", 0.28809, "stability_priority", 1.00000),
    ("PAT_003", 1, "PROTO_STIFF", "knee-mobility", 0.03606, "stability_priority", 1.00000),
    ("PAT_003", 2, "PROTO_STEADY", "steadying", 0.15555, "stability_priority", 1.00000),
    ("PAT_003", 3, "PROTO_PROPULSE", "push-off", 0.17450, "stability_priority", 1.00000),
    ("PAT_004", 1, "PROTO_FATIGUE", "endurance", 0.02521, "stability_priority", 1.00000),
    ("PAT_004", 2, "PROTO_DRAG", "toe-clearance", 0.10050, "stability_priority", 1.00000),
    ("PAT_004", 3, "PROTO_BALANCE", "balance", 0.34050, "stability_priority", 1.00000),
    ("PAT_005", 1, "PROTO_PROPULSE", "push-off", 0.04798, "stability_priority", 1.00000),
    ("PAT_005", 2, "PROTO_STEADY", "steadying", 0.12450, "stability_priority", 1.00000),
    ("PAT_005", 3, "PROTO_STIFF", "knee-mobility", 0.17158, "stability_priority", 1.00000),
]


def load_result() -> pd.DataFrame:
    assert RESULT_PATH.exists(), f"Result file not found: {RESULT_PATH}"
    return pd.read_csv(RESULT_PATH)


def test_required_columns_and_row_count():
    result = load_result()
    expected_columns = [
        "patient_id",
        "rank",
        "prototype_id",
        "therapy_track",
        "distance",
        "selected_profile",
        "validation_accuracy",
    ]
    assert list(result.columns) == expected_columns
    assert len(result) == 15


def test_exact_rankings():
    result = load_result().copy()
    result["distance"] = result["distance"].round(5)
    result["validation_accuracy"] = result["validation_accuracy"].round(5)

    expected = pd.DataFrame(
        EXPECTED_ROWS,
        columns=[
            "patient_id",
            "rank",
            "prototype_id",
            "therapy_track",
            "distance",
            "selected_profile",
            "validation_accuracy",
        ],
    )

    pd.testing.assert_frame_equal(result.reset_index(drop=True), expected, check_exact=True)


def test_three_ranks_per_patient():
    result = load_result()
    counts = result.groupby("patient_id")["rank"].count()
    assert (counts == 3).all()
    assert set(result["rank"]) == {1, 2, 3}
