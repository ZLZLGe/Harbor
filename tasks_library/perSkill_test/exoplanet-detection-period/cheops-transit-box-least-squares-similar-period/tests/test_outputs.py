import os
import re

import pytest


class TestPlanetPeriod:
    EXPECTED_PERIOD = 3.74216
    TOLERANCE = 0.01

    def get_output_path(self):
        for path in ("/root/planet_period.txt", "planet_period.txt"):
            if os.path.exists(path):
                return path
        return None

    def test_output_file_exists(self):
        assert self.get_output_path() is not None, "Expected /root/planet_period.txt to exist"

    def test_output_format(self):
        path = self.get_output_path()
        if path is None:
            pytest.skip("planet_period.txt not found")

        with open(path, encoding="utf-8") as fh:
            content = fh.read().strip()

        assert re.fullmatch(r"[0-9]+(?:\.[0-9]{1,5})?", content), f"Invalid format: {content!r}"

    def test_output_is_positive_float(self):
        path = self.get_output_path()
        if path is None:
            pytest.skip("planet_period.txt not found")

        with open(path, encoding="utf-8") as fh:
            content = fh.read().strip()

        value = float(content)
        assert value > 0, f"Period must be positive, got {value}"

    def test_period_matches_expected_signal(self):
        path = self.get_output_path()
        if path is None:
            pytest.skip("planet_period.txt not found")

        with open(path, encoding="utf-8") as fh:
            content = fh.read().strip()

        period = float(content)
        assert abs(period - self.EXPECTED_PERIOD) < self.TOLERANCE, (
            f"Recovered period {period:.5f} is not within ±{self.TOLERANCE:.2f} days "
            f"of {self.EXPECTED_PERIOD:.5f}"
        )
