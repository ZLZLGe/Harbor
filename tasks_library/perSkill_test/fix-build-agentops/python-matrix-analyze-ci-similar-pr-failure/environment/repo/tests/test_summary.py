import unittest

from prstatus.summary import build_report_title, format_python_job


class TestJobSummary(unittest.TestCase):
    def test_format_python_job_preserves_dot(self) -> None:
        self.assertEqual(format_python_job("3.10"), "python-3.10")
        self.assertEqual(format_python_job("3.11"), "python-3.11")

    def test_build_report_title_uses_matrix_label(self) -> None:
        self.assertEqual(build_report_title(1421, "3.11"), "PR #1421 / python-3.11")


if __name__ == "__main__":
    unittest.main()
