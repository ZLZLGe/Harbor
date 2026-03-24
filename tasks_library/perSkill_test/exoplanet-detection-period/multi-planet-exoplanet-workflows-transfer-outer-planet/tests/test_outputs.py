import os
import re

import pytest


class TestOuterPlanetPeriod:
    EXPECTED_OUTER_PERIOD = 9.27463
    INNER_PERIOD = 3.91842
    TOLERANCE = 0.05

    def get_output_path(self):
        for path in ("/root/outer_planet_period.txt", "outer_planet_period.txt"):
            if os.path.exists(path):
                return path
        return None

    def read_output(self):
        path = self.get_output_path()
        if path is None:
            pytest.fail("Missing output file: /root/outer_planet_period.txt")
        with open(path) as fh:
            return fh.read().strip()

    def test_output_file_exists(self):
        assert self.get_output_path() is not None

    def test_output_format(self):
        content = self.read_output()
        assert re.fullmatch(r"\d+\.\d{5}", content), (
            "Output must be a single number with exactly 5 decimal places"
        )

    def test_output_is_outer_planet_range(self):
        period = float(self.read_output())
        assert 6.0 < period < 12.0, f"Recovered period {period:.5f} is outside the outer-planet search range"

    def test_output_matches_outer_planet(self):
        period = float(self.read_output())
        assert abs(period - self.EXPECTED_OUTER_PERIOD) < self.TOLERANCE, (
            f"Recovered period {period:.5f} does not match the expected outer period "
            f"{self.EXPECTED_OUTER_PERIOD:.5f} within ±{self.TOLERANCE:.2f} days"
        )

    def test_output_is_not_inner_planet_alias(self):
        period = float(self.read_output())
        assert abs(period - self.INNER_PERIOD) > 1.0, (
            f"Recovered period {period:.5f} is too close to the dominant inner planet "
            f"{self.INNER_PERIOD:.5f}"
        )
