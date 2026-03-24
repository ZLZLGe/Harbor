import json
import os

import pytest


class TestEphemerisOutput:
    EXPECTED_PERIOD = 4.23760
    EXPECTED_REFERENCE_EPOCH = 2459821.68829
    EXPECTED_MIDPOINTS = [
        2459821.65375,
        2459825.95959,
        2459834.41833,
        2459838.63225,
        2459847.10398,
    ]
    PERIOD_TOLERANCE = 0.02
    EPOCH_TOLERANCE = 0.08
    MIDPOINT_TOLERANCE = 0.10

    def get_output_path(self):
        for path in ("/root/ephemeris.json", "ephemeris.json"):
            if os.path.exists(path):
                return path
        return None

    def read_output(self):
        path = self.get_output_path()
        if path is None:
            pytest.fail("Missing output file: /root/ephemeris.json")
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def test_output_file_exists(self):
        assert self.get_output_path() is not None

    def test_output_keys_match_schema(self):
        payload = self.read_output()
        assert set(payload) == {
            "period_days",
            "reference_mid_transit_bjd_tdb",
            "observed_mid_transits_bjd_tdb",
            "time_system",
        }

    def test_output_types(self):
        payload = self.read_output()
        assert isinstance(payload["period_days"], (int, float))
        assert isinstance(payload["reference_mid_transit_bjd_tdb"], (int, float))
        assert isinstance(payload["observed_mid_transits_bjd_tdb"], list)
        assert all(isinstance(value, (int, float)) for value in payload["observed_mid_transits_bjd_tdb"])
        assert payload["time_system"] == "BJD_TDB"

    def test_period_matches_reference_solution(self):
        payload = self.read_output()
        period = float(payload["period_days"])
        assert abs(period - self.EXPECTED_PERIOD) < self.PERIOD_TOLERANCE, (
            f"Recovered period {period:.5f} does not match expected {self.EXPECTED_PERIOD:.5f} "
            f"within ±{self.PERIOD_TOLERANCE:.2f} days"
        )

    def test_reference_epoch_matches_reference_solution(self):
        payload = self.read_output()
        epoch = float(payload["reference_mid_transit_bjd_tdb"])
        assert abs(epoch - self.EXPECTED_REFERENCE_EPOCH) < self.EPOCH_TOLERANCE, (
            f"Reference epoch {epoch:.5f} does not match expected {self.EXPECTED_REFERENCE_EPOCH:.5f} "
            f"within ±{self.EPOCH_TOLERANCE:.2f} days"
        )

    def test_midpoints_are_sorted_and_recover_campaign_events(self):
        payload = self.read_output()
        reported = [float(value) for value in payload["observed_mid_transits_bjd_tdb"]]
        assert reported == sorted(reported), "Observed mid-transit times must be in ascending order"
        assert len(reported) >= 4, "Expected at least four observed mid-transit times"

        for expected in self.EXPECTED_MIDPOINTS:
            assert any(abs(expected - value) < self.MIDPOINT_TOLERANCE for value in reported), (
                f"No reported mid-transit time is close to expected campaign event {expected:.5f}"
            )

    def test_midpoints_are_consistent_with_reported_ephemeris(self):
        payload = self.read_output()
        period = float(payload["period_days"])
        epoch = float(payload["reference_mid_transit_bjd_tdb"])
        reported = [float(value) for value in payload["observed_mid_transits_bjd_tdb"]]

        for value in reported:
            cycles = round((value - epoch) / period)
            predicted = epoch + cycles * period
            assert abs(predicted - value) < self.MIDPOINT_TOLERANCE, (
                f"Reported midpoint {value:.5f} is not consistent with the reported ephemeris"
            )
