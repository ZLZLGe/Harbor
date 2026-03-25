import os
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_PATH = Path(os.environ.get("INPUT_PATH", "/root/data/wearable_ppg_session.csv"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/ppg_clean_segments.csv"))
GAP_THRESHOLD_SECONDS = 1.2
MIN_POINTS = 180


def centered_time_rolling_mean(values, timestamps, window_seconds=2.0):
    index = pd.to_timedelta(timestamps, unit="s")
    series = pd.Series(values.to_numpy(), index=index)
    return series.rolling(f"{window_seconds}s", center=True, min_periods=1).mean().to_numpy()


def mark_saturated_spikes(frame):
    local_baseline = frame["ppg_signal"].rolling(window=13, center=True, min_periods=1).median()
    residual = frame["ppg_signal"] - local_baseline
    residual_median = float(np.median(residual))
    mad = float(np.median(np.abs(residual - residual_median)))
    threshold = max(0.06, 6.0 * 1.4826 * mad)
    return residual.abs() > threshold


class WearablePPGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = pd.read_csv(INPUT_PATH).sort_values("timestamp").reset_index(drop=True)
        good = cls.source.loc[cls.source["quality_flag"] == 0].copy().reset_index(drop=True)
        clean = good.loc[~mark_saturated_spikes(good)].copy().reset_index(drop=True)
        clean["gap"] = clean["timestamp"].diff().fillna(0.0)
        clean["candidate_segment"] = (clean["gap"] > GAP_THRESHOLD_SECONDS).cumsum() + 1

        expected_segments = []
        expected_rows = []
        for group in (g.copy().reset_index(drop=True) for _, g in clean.groupby("candidate_segment", sort=True)):
            if len(group) < MIN_POINTS:
                continue

            segment_id = len(expected_segments) + 1
            group["timestamp_key"] = group["timestamp"].round(5)
            group["expected_segment_id"] = segment_id
            expected_segments.append(group)
            expected_rows.append(group[["timestamp_key", "expected_segment_id"]])

        cls.expected_segments = expected_segments
        cls.expected_output = pd.concat(expected_rows, ignore_index=True)

    def load_output(self):
        self.assertTrue(OUTPUT_PATH.exists(), "缺少 /root/ppg_clean_segments.csv")
        return pd.read_csv(OUTPUT_PATH)

    def test_output_exists(self):
        self.assertTrue(OUTPUT_PATH.exists(), "缺少 /root/ppg_clean_segments.csv")

    def test_required_columns_exist(self):
        output = self.load_output()
        required = {"timestamp", "normalized_signal", "segment_id"}
        self.assertTrue(required.issubset(output.columns), f"输出缺少必需列: {required - set(output.columns)}")

    def test_output_uses_expected_retained_samples(self):
        output = self.load_output().copy()
        output["timestamp_key"] = output["timestamp"].round(5)
        produced_timestamps = output["timestamp_key"].tolist()
        expected_timestamps = self.expected_output["timestamp_key"].tolist()

        self.assertEqual(produced_timestamps, sorted(produced_timestamps), "timestamp 必须升序排列")
        self.assertEqual(len(produced_timestamps), len(set(produced_timestamps)), "输出里不应出现重复 timestamp")
        self.assertEqual(produced_timestamps, expected_timestamps, "输出样本不符合题面声明的筛选规则")

    def test_output_rows_map_back_to_good_quality_source(self):
        output = self.load_output().copy()
        source = self.source.copy()
        output["timestamp_key"] = output["timestamp"].round(5)
        source["timestamp_key"] = source["timestamp"].round(5)

        merged = output.merge(
            source[["timestamp_key", "quality_flag"]],
            on="timestamp_key",
            how="left",
            validate="one_to_one",
        )
        self.assertFalse(merged["quality_flag"].isna().any(), "输出里出现了输入中不存在的 timestamp")
        self.assertTrue((merged["quality_flag"] == 0).all(), "输出里仍包含低质量样本")

    def test_segment_ids_follow_expected_segments(self):
        output = self.load_output().copy()
        expected_ids = list(range(1, len(self.expected_segments) + 1))
        actual_ids = sorted(output["segment_id"].unique().tolist())
        self.assertEqual(actual_ids, expected_ids, "segment_id 必须从 1 开始连续递增")

        grouped = list(output.groupby("segment_id", sort=True))
        self.assertEqual(len(grouped), len(self.expected_segments), "稳定片段数量不正确")

        for expected_id, (_, group), expected_source in zip(expected_ids, grouped, self.expected_segments):
            timestamps = group["timestamp"].round(5).tolist()
            expected_timestamps = expected_source["timestamp_key"].tolist()
            self.assertEqual(timestamps, expected_timestamps, f"segment_id={expected_id} 的时间范围不正确")
            self.assertTrue(group.index.to_series().diff().fillna(1).eq(1).all(), "同一片段的样本必须连续出现")
            self.assertGreaterEqual(len(group), MIN_POINTS, "保留片段的样本数必须不少于 180")

    def test_normalized_signal_is_centered_and_detrended(self):
        output = self.load_output().copy()
        source = self.source.copy()
        output["timestamp_key"] = output["timestamp"].round(5)
        source["timestamp_key"] = source["timestamp"].round(5)

        for _, group in output.groupby("segment_id", sort=True):
            self.assertFalse(group["normalized_signal"].isna().any(), "normalized_signal 不能包含 NaN")
            self.assertLessEqual(abs(float(group["normalized_signal"].median())), 0.01, "片段中位数没有回到零线附近")

            merged = group.merge(
                source[["timestamp_key", "ppg_signal"]],
                on="timestamp_key",
                how="left",
                validate="one_to_one",
            )
            self.assertFalse(merged["ppg_signal"].isna().any(), "输出片段包含未知 timestamp")

            raw_baseline = centered_time_rolling_mean(merged["ppg_signal"], merged["timestamp"])
            clean_baseline = centered_time_rolling_mean(merged["normalized_signal"], merged["timestamp"])

            raw_range = float(np.max(raw_baseline) - np.min(raw_baseline))
            clean_range = float(np.max(clean_baseline) - np.min(clean_baseline))
            self.assertLessEqual(clean_range, raw_range * 0.3 + 1e-9, "慢漂移压低幅度不足 70%")


if __name__ == "__main__":
    unittest.main()
