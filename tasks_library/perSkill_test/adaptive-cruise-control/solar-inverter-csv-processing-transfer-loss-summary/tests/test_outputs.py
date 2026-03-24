from pathlib import Path

import pandas as pd


def locate_task_root() -> Path:
    return Path(__file__).resolve().parents[1]


def locate_output_file() -> Path:
    candidates = [
        Path("/root/inverter_loss_summary.csv"),
        locate_task_root() / "inverter_loss_summary.csv",
    ]
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except PermissionError:
            continue
    raise AssertionError("inverter_loss_summary.csv was not created")


class TestInverterLossSummary:
    def test_output_matches_expected_summary(self):
        output_path = locate_output_file()
        df = pd.read_csv(output_path)

        expected = pd.DataFrame(
            [
                {
                    "inverter_id": "INV-A",
                    "interval_type": "downtime",
                    "interval_start": "2026-06-18 08:30",
                    "interval_end": "2026-06-18 08:45",
                    "sample_count": 2,
                    "baseline_kwh": 12.50,
                    "estimated_lost_kwh": 25.00,
                    "root_cause_label": "planned_maintenance",
                },
                {
                    "inverter_id": "INV-A",
                    "interval_type": "curtailment",
                    "interval_start": "2026-06-18 09:30",
                    "interval_end": "2026-06-18 09:45",
                    "sample_count": 2,
                    "baseline_kwh": 11.00,
                    "estimated_lost_kwh": 5.00,
                    "root_cause_label": "grid_curtailment",
                },
                {
                    "inverter_id": "INV-B",
                    "interval_type": "downtime",
                    "interval_start": "2026-06-18 08:30",
                    "interval_end": "2026-06-18 08:30",
                    "sample_count": 1,
                    "baseline_kwh": 10.65,
                    "estimated_lost_kwh": 10.65,
                    "root_cause_label": "communications_outage",
                },
                {
                    "inverter_id": "INV-B",
                    "interval_type": "curtailment",
                    "interval_start": "2026-06-18 09:15",
                    "interval_end": "2026-06-18 09:30",
                    "sample_count": 2,
                    "baseline_kwh": 10.65,
                    "estimated_lost_kwh": 0.40,
                    "root_cause_label": "grid_curtailment",
                },
                {
                    "inverter_id": "INV-B",
                    "interval_type": "downtime",
                    "interval_start": "2026-06-18 10:00",
                    "interval_end": "2026-06-18 10:15",
                    "sample_count": 2,
                    "baseline_kwh": 10.80,
                    "estimated_lost_kwh": 21.60,
                    "root_cause_label": "communications_outage",
                },
                {
                    "inverter_id": "INV-C",
                    "interval_type": "curtailment",
                    "interval_start": "2026-06-18 09:30",
                    "interval_end": "2026-06-18 09:45",
                    "sample_count": 2,
                    "baseline_kwh": 14.15,
                    "estimated_lost_kwh": 0.80,
                    "root_cause_label": "grid_curtailment",
                },
                {
                    "inverter_id": "INV-C",
                    "interval_type": "downtime",
                    "interval_start": "2026-06-18 10:15",
                    "interval_end": "2026-06-18 10:45",
                    "sample_count": 3,
                    "baseline_kwh": 14.00,
                    "estimated_lost_kwh": 42.00,
                    "root_cause_label": "planned_maintenance",
                },
            ]
        )

        assert list(df.columns) == [
            "inverter_id",
            "interval_type",
            "interval_start",
            "interval_end",
            "sample_count",
            "baseline_kwh",
            "estimated_lost_kwh",
            "root_cause_label",
        ]

        df = df.sort_values(["inverter_id", "interval_start"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(df, expected, check_dtype=False)

    def test_output_shape_and_labels(self):
        output_path = locate_output_file()
        df = pd.read_csv(output_path)

        assert len(df) == 7
        assert set(df["interval_type"]) == {"downtime", "curtailment"}
        assert set(df["root_cause_label"]) == {
            "planned_maintenance",
            "communications_outage",
            "grid_curtailment",
        }
