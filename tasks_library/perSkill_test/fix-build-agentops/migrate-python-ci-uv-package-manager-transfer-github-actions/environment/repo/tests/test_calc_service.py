import unittest

from calc_service import summarize_scores


class SummarizeScoresTest(unittest.TestCase):
    def test_sorts_highest_score_first(self) -> None:
        result = summarize_scores({"beta": 11, "alpha": 11, "gamma": 7})
        self.assertEqual(result, ["alpha:11", "beta:11", "gamma:7"])


if __name__ == "__main__":
    unittest.main()
