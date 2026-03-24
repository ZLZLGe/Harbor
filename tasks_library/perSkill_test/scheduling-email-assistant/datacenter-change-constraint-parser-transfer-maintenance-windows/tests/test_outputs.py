import json
from pathlib import Path


OUTPUT_PATH = Path("/root/change_window_constraints.json")

EXPECTED = {
    "chg-701": {
        "system": "core-auth-db",
        "approved_windows": [
            {
                "start_date": "2026-07-11",
                "end_date": "2026-07-11",
                "start_time": "01:00",
                "end_time": "03:30",
                "timezone": "UTC",
            }
        ],
        "freeze_periods": [
            {
                "start_date": "2026-07-14",
                "end_date": "2026-07-16",
                "reason": "quarter-close reporting",
            }
        ],
        "prohibited_dates": [
            {
                "date": "2026-07-18",
                "reason": "the onboarding campaign goes live that day",
            }
        ],
        "maximum_outage_minutes": 30,
        "sequencing_constraints": [
            "Sequence-wise, the replica promotion has to finish before the primary reboot, and health checks must pass before login traffic is restored."
        ],
        "rejected_window": "2026-07-12",
    },
    "chg-702": {
        "system": "backbone-optics",
        "approved_windows": [
            {
                "start_date": "2026-08-02",
                "end_date": "2026-08-02",
                "start_time": "22:00",
                "end_time": "23:30",
                "timezone": "PDT",
            }
        ],
        "freeze_periods": [
            {
                "start_date": "2026-08-05",
                "end_date": "2026-08-07",
                "reason": "the regional disaster drill",
            }
        ],
        "prohibited_dates": [
            {
                "date": "2026-08-09",
                "reason": "the stadium event traffic load",
            }
        ],
        "maximum_outage_minutes": 12,
        "sequencing_constraints": [
            "The BGP session drain must complete before the optics swap, and remote hands need to confirm the spare line is lit before we cut over."
        ],
        "rejected_window": "2026-08-03",
    },
    "chg-703": {
        "system": "storage-cluster-a",
        "approved_windows": [
            {
                "start_date": "2026-08-21",
                "end_date": "2026-08-21",
                "start_time": "21:00",
                "end_time": "23:00",
                "timezone": "CEST",
            },
            {
                "start_date": "2026-08-22",
                "end_date": "2026-08-22",
                "start_time": "21:00",
                "end_time": "23:00",
                "timezone": "CEST",
            },
        ],
        "freeze_periods": [
            {
                "start_date": "2026-08-28",
                "end_date": "2026-08-31",
                "reason": "month-end freeze",
            }
        ],
        "prohibited_dates": [
            {
                "date": "2026-08-24",
                "reason": "the backup restore rehearsal is booked all day",
            }
        ],
        "maximum_outage_minutes": 20,
        "sequencing_constraints": [
            "Snapshot validation must finish before controller failover starts.",
            "Node A has to be upgraded and rejoined before Node B enters maintenance.",
        ],
        "rejected_window": None,
    },
    "chg-704": {
        "system": "payment-hsm",
        "approved_windows": [
            {
                "start_date": "2026-09-08",
                "end_date": "2026-09-08",
                "start_time": "01:30",
                "end_time": "02:30",
                "timezone": "SGT",
            }
        ],
        "freeze_periods": [
            {
                "start_date": "2026-09-03",
                "end_date": "2026-09-06",
                "reason": "the annual resilience exercise",
            }
        ],
        "prohibited_dates": [
            {
                "date": "2026-09-10",
                "reason": "the acquiring partner certification run",
            }
        ],
        "maximum_outage_minutes": 5,
        "sequencing_constraints": [
            "Promote the secondary HSM before rebooting the primary, and finish tokenization smoke tests before merchant traffic is resumed."
        ],
        "rejected_window": "2026-09-07",
    },
}


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"


def test_schema_and_semantics():
    with OUTPUT_PATH.open("r", encoding="utf-8") as f:
        actual = json.load(f)

    assert list(actual.keys()) == ["changes"], "Top-level JSON must only contain 'changes'."

    changes = actual["changes"]
    ids = [entry["change_id"] for entry in changes]
    assert ids == sorted(EXPECTED), "Changes must be sorted by change_id."
    assert len(changes) == len(EXPECTED), "Unexpected number of change records."

    for entry in changes:
        change_id = entry["change_id"]
        assert change_id in EXPECTED, f"Unexpected change_id: {change_id}"
        expected = EXPECTED[change_id]

        assert entry["system"] == expected["system"]
        assert entry["approved_windows"] == expected["approved_windows"]
        assert entry["freeze_periods"] == expected["freeze_periods"]
        assert entry["prohibited_dates"] == expected["prohibited_dates"]
        assert entry["maximum_outage_minutes"] == expected["maximum_outage_minutes"]
        assert isinstance(entry["maximum_outage_minutes"], int)
        assert entry["sequencing_constraints"] == expected["sequencing_constraints"]

        approved_dates = [window["start_date"] for window in entry["approved_windows"]]
        assert approved_dates == sorted(approved_dates), f"approved_windows not sorted for {change_id}"
        freeze_dates = [period["start_date"] for period in entry["freeze_periods"]]
        assert freeze_dates == sorted(freeze_dates), f"freeze_periods not sorted for {change_id}"
        blocked_dates = [period["date"] for period in entry["prohibited_dates"]]
        assert blocked_dates == sorted(blocked_dates), f"prohibited_dates not sorted for {change_id}"

        rejected_window = expected["rejected_window"]
        if rejected_window is not None:
            assert rejected_window not in approved_dates, f"Rejected window leaked into approved_windows for {change_id}"

        for sentence in entry["sequencing_constraints"]:
            assert sentence.endswith("."), f"Sequencing constraint must be a sentence for {change_id}"


if __name__ == "__main__":
    test_output_exists()
    test_schema_and_semantics()
    print("Datacenter maintenance constraints verified.")
