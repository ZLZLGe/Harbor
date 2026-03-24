import csv
import os
import re

import pytest


class TestValidatedPeriod:
    EXPECTED_PERIOD = 7.84216
    HALF_ALIAS = 3.92108
    DOUBLE_ALIAS = 15.68432
    TOLERANCE = 0.03

    def get_output_path(self):
        for path in ("/root/validated_period.txt", "validated_period.txt"):
            if os.path.exists(path):
                return path
        return None

    def read_output(self):
        path = self.get_output_path()
        if path is None:
            pytest.fail("Missing output file: /root/validated_period.txt")
        with open(path) as fh:
            return fh.read().strip()

    def test_output_file_exists(self):
        assert self.get_output_path() is not None

    def test_output_format(self):
        content = self.read_output()
        assert re.fullmatch(r"\d+\.\d{5}", content), (
            "Output must be a single number with exactly 5 decimal places"
        )

    def test_output_matches_true_period(self):
        period = float(self.read_output())
        assert abs(period - self.EXPECTED_PERIOD) < self.TOLERANCE, (
            f"Validated period {period:.5f} does not match the true period "
            f"{self.EXPECTED_PERIOD:.5f} within ±{self.TOLERANCE:.2f} days"
        )

    def test_output_rejects_half_alias(self):
        period = float(self.read_output())
        assert abs(period - self.HALF_ALIAS) > 0.2, (
            f"Validated period {period:.5f} is too close to the 0.5x alias "
            f"{self.HALF_ALIAS:.5f}"
        )

    def test_output_rejects_double_alias(self):
        period = float(self.read_output())
        assert abs(period - self.DOUBLE_ALIAS) > 0.2, (
            f"Validated period {period:.5f} is too close to the 2x alias "
            f"{self.DOUBLE_ALIAS:.5f}"
        )

    def test_output_matches_candidate_shortlist(self):
        path = "/root/data/candidate_periods.csv"
        if not os.path.exists(path):
            pytest.skip("Candidate shortlist not available")

        with open(path, newline="") as handle:
            candidates = [float(row["period_days"]) for row in csv.DictReader(handle)]

        period = float(self.read_output())
        assert any(abs(period - candidate) < 0.05 for candidate in candidates), (
            f"Validated period {period:.5f} does not match any listed candidate"
        )
