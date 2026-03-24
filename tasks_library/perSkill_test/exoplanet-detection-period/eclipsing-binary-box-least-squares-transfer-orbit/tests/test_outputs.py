import os
import re

import pytest


class TestBinaryPeriod:
    EXPECTED_PERIOD = 3.18472
    HALF_PERIOD_ALIAS = EXPECTED_PERIOD / 2.0
    TOLERANCE = 0.02

    def get_output_path(self):
        for path in ("/root/binary_period.txt", "binary_period.txt"):
            if os.path.exists(path):
                return path
        return None

    def test_output_file_exists(self):
        assert self.get_output_path() is not None, "Expected /root/binary_period.txt to exist"

    def test_output_format(self):
        path = self.get_output_path()
        if path is None:
            pytest.skip("binary_period.txt not found")

        with open(path, encoding="utf-8") as fh:
            content = fh.read().strip()

        assert re.fullmatch(r"[0-9]+(?:\.[0-9]{1,5})?", content), f"Invalid format: {content!r}"

    def test_output_is_positive_float(self):
        path = self.get_output_path()
        if path is None:
            pytest.skip("binary_period.txt not found")

        with open(path, encoding="utf-8") as fh:
            content = fh.read().strip()

        value = float(content)
        assert value > 0, f"Period must be positive, got {value}"

    def test_period_matches_orbital_cycle(self):
        path = self.get_output_path()
        if path is None:
            pytest.skip("binary_period.txt not found")

        with open(path, encoding="utf-8") as fh:
            content = fh.read().strip()

        period = float(content)
        assert abs(period - self.EXPECTED_PERIOD) < self.TOLERANCE, (
            f"Recovered orbital period {period:.5f} is not within ±{self.TOLERANCE:.2f} days "
            f"of {self.EXPECTED_PERIOD:.5f}"
        )

    def test_period_is_not_half_period_alias(self):
        path = self.get_output_path()
        if path is None:
            pytest.skip("binary_period.txt not found")

        with open(path, encoding="utf-8") as fh:
            content = fh.read().strip()

        period = float(content)
        assert abs(period - self.HALF_PERIOD_ALIAS) > 0.05, (
            f"Recovered value {period:.5f} looks like the common half-period alias "
            f"{self.HALF_PERIOD_ALIAS:.5f} instead of the orbital period"
        )
