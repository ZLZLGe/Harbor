import json
import os


OUTPUT_FILE = "/app/workspace/parking_occupancy.json"
TOP_LEVEL_KEYS = {"captures", "peak_timepoints", "peak_total_occupied"}
CAPTURE_KEYS = {"timepoint", "zone_counts", "total_occupied"}
ZONE_KEYS = {"north", "center", "south"}
EXPECTED = {
    "captures": [
        {
            "timepoint": "2026-03-14_0630",
            "zone_counts": {"north": 1, "center": 2, "south": 2},
            "total_occupied": 5,
        },
        {
            "timepoint": "2026-03-14_0915",
            "zone_counts": {"north": 3, "center": 2, "south": 4},
            "total_occupied": 9,
        },
        {
            "timepoint": "2026-03-14_1200",
            "zone_counts": {"north": 4, "center": 3, "south": 4},
            "total_occupied": 11,
        },
        {
            "timepoint": "2026-03-14_1745",
            "zone_counts": {"north": 4, "center": 4, "south": 3},
            "total_occupied": 11,
        },
        {
            "timepoint": "2026-03-14_2100",
            "zone_counts": {"north": 2, "center": 2, "south": 3},
            "total_occupied": 7,
        },
    ],
    "peak_timepoints": ["2026-03-14_1200", "2026-03-14_1745"],
    "peak_total_occupied": 11,
}


def test_output_contract() -> None:
    assert os.path.exists(OUTPUT_FILE), "Missing /app/workspace/parking_occupancy.json"

    with open(OUTPUT_FILE, encoding="utf-8") as handle:
        payload = json.load(handle)

    assert isinstance(payload, dict), "Output must be a JSON object."
    assert set(payload.keys()) == TOP_LEVEL_KEYS, (
        "Top-level keys mismatch.\n"
        f"Actual: {sorted(payload.keys())}\n"
        f"Expected: {sorted(TOP_LEVEL_KEYS)}"
    )

    captures = payload["captures"]
    assert isinstance(captures, list), "`captures` must be a list."
    assert captures, "`captures` must not be empty."

    seen_timepoints = []
    totals = []
    for capture in captures:
        assert isinstance(capture, dict), "Each capture must be an object."
        assert set(capture.keys()) == CAPTURE_KEYS, (
            "Capture keys mismatch.\n"
            f"Actual: {sorted(capture.keys())}\n"
            f"Expected: {sorted(CAPTURE_KEYS)}"
        )

        timepoint = capture["timepoint"]
        zone_counts = capture["zone_counts"]
        total_occupied = capture["total_occupied"]

        assert isinstance(timepoint, str) and timepoint, "`timepoint` must be a non-empty string."
        assert isinstance(zone_counts, dict), "`zone_counts` must be an object."
        assert set(zone_counts.keys()) == ZONE_KEYS, (
            "zone_counts keys mismatch.\n"
            f"Actual: {sorted(zone_counts.keys())}\n"
            f"Expected: {sorted(ZONE_KEYS)}"
        )
        assert isinstance(total_occupied, int) and not isinstance(total_occupied, bool), (
            "`total_occupied` must be an integer."
        )

        zone_total = 0
        for zone_name, value in zone_counts.items():
            assert isinstance(value, int) and not isinstance(value, bool), (
                f"{zone_name} count must be an integer."
            )
            assert value >= 0, f"{zone_name} count must be non-negative."
            zone_total += value

        assert total_occupied == zone_total, (
            "total_occupied must equal the sum of zone_counts.\n"
            f"timepoint={timepoint!r}, total_occupied={total_occupied}, zone_total={zone_total}"
        )

        seen_timepoints.append(timepoint)
        totals.append(total_occupied)

    assert seen_timepoints == sorted(seen_timepoints), (
        "captures must be sorted by timepoint.\n"
        f"Actual order: {seen_timepoints}"
    )

    expected_peak = max(totals)
    actual_peak = payload["peak_total_occupied"]
    assert isinstance(actual_peak, int) and not isinstance(actual_peak, bool), (
        "`peak_total_occupied` must be an integer."
    )
    assert actual_peak == expected_peak, (
        "peak_total_occupied mismatch.\n"
        f"Actual: {actual_peak}\n"
        f"Expected: {expected_peak}"
    )

    peak_timepoints = payload["peak_timepoints"]
    assert isinstance(peak_timepoints, list), "`peak_timepoints` must be a list."
    assert all(isinstance(item, str) and item for item in peak_timepoints), (
        "`peak_timepoints` must only contain non-empty strings."
    )
    expected_timepoints = sorted(
        capture["timepoint"] for capture in captures if capture["total_occupied"] == actual_peak
    )
    assert peak_timepoints == expected_timepoints, (
        "peak_timepoints mismatch.\n"
        f"Actual: {peak_timepoints}\n"
        f"Expected: {expected_timepoints}"
    )

    assert payload == EXPECTED, (
        "Output JSON does not match the oracle exactly.\n"
        f"Actual: {payload}\n"
        f"Expected: {EXPECTED}"
    )
