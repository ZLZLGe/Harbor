from pathlib import Path

import pandas as pd


def locate_task_root() -> Path:
    return Path(__file__).resolve().parents[1]


def locate_output_file() -> Path:
    candidates = [
        Path("/root/shipment_excursion_audit.csv"),
        locate_task_root() / "shipment_excursion_audit.csv",
    ]
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except PermissionError:
            continue
    raise AssertionError("shipment_excursion_audit.csv was not created")


class TestShipmentExcursionAudit:
    def test_output_matches_expected_audit(self):
        output_path = locate_output_file()
        df = pd.read_csv(output_path)

        expected = pd.DataFrame(
            [
                {
                    "shipment_id": "SHP-001",
                    "excursion_start": "2026-02-12 08:01",
                    "excursion_end": "2026-02-12 08:04",
                    "duration_minutes": 4,
                    "peak_temperature_c": 5.8,
                    "door_open_during_excursion": "yes",
                },
                {
                    "shipment_id": "SHP-001",
                    "excursion_start": "2026-02-12 08:06",
                    "excursion_end": "2026-02-12 08:07",
                    "duration_minutes": 2,
                    "peak_temperature_c": 5.3,
                    "door_open_during_excursion": "no",
                },
                {
                    "shipment_id": "SHP-002",
                    "excursion_start": "2026-02-12 09:16",
                    "excursion_end": "2026-02-12 09:17",
                    "duration_minutes": 2,
                    "peak_temperature_c": 7.4,
                    "door_open_during_excursion": "no",
                },
                {
                    "shipment_id": "SHP-002",
                    "excursion_start": "2026-02-12 09:19",
                    "excursion_end": "2026-02-12 09:23",
                    "duration_minutes": 5,
                    "peak_temperature_c": 7.6,
                    "door_open_during_excursion": "yes",
                },
                {
                    "shipment_id": "SHP-003",
                    "excursion_start": "2026-02-12 10:02",
                    "excursion_end": "2026-02-12 10:02",
                    "duration_minutes": 1,
                    "peak_temperature_c": 4.7,
                    "door_open_during_excursion": "no",
                },
                {
                    "shipment_id": "SHP-003",
                    "excursion_start": "2026-02-12 10:04",
                    "excursion_end": "2026-02-12 10:06",
                    "duration_minutes": 3,
                    "peak_temperature_c": 5.1,
                    "door_open_during_excursion": "yes",
                },
                {
                    "shipment_id": "SHP-003",
                    "excursion_start": "2026-02-12 10:08",
                    "excursion_end": "2026-02-12 10:10",
                    "duration_minutes": 3,
                    "peak_temperature_c": 5.0,
                    "door_open_during_excursion": "no",
                },
            ]
        )

        assert list(df.columns) == [
            "shipment_id",
            "excursion_start",
            "excursion_end",
            "duration_minutes",
            "peak_temperature_c",
            "door_open_during_excursion",
        ]

        df = df.sort_values(["shipment_id", "excursion_start"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(df, expected, check_dtype=False)

    def test_output_has_no_extra_rows(self):
        output_path = locate_output_file()
        df = pd.read_csv(output_path)
        assert len(df) == 7
        assert set(df["door_open_during_excursion"]) == {"yes", "no"}
