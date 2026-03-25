import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_PATH = Path("/root/data/occultation_session.csv")
OUTPUT_PATH = Path("/root/occultation_windows.json")
GAP_THRESHOLD_SECONDS = 90
MIN_POINTS = 25


def rolling_median(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, center=True, min_periods=1).median()


class OccultationWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = pd.read_csv(INPUT_PATH).sort_values("time_jd").reset_index(drop=True)
        cls.good_quality = cls.source[cls.source["frame_quality"] == 0].copy().reset_index(drop=True)

    def load_output(self):
        self.assertTrue(OUTPUT_PATH.exists(), "缺少 /root/occultation_windows.json")
        with OUTPUT_PATH.open() as f:
            return json.load(f)

    def test_output_exists(self):
        self.assertTrue(OUTPUT_PATH.exists(), "缺少 /root/occultation_windows.json")

    def test_top_level_contract(self):
        payload = self.load_output()
        self.assertIsInstance(payload, dict, "输出必须是 JSON 对象")
        self.assertEqual(payload.get("source_file"), str(INPUT_PATH), "source_file 必须写成输入文件路径")
        self.assertEqual(payload.get("gap_threshold_seconds"), GAP_THRESHOLD_SECONDS, "gap_threshold_seconds 必须为 90")
        self.assertIn("windows", payload, "输出缺少 windows")
        self.assertIsInstance(payload["windows"], list, "windows 必须是数组")
        self.assertGreater(len(payload["windows"]), 0, "至少应输出一个有效窗口")

    def test_windows_follow_final_retained_points(self):
        payload = self.load_output()
        gap_days = GAP_THRESHOLD_SECONDS / 86400.0
        previous_end_time = None

        for index, window in enumerate(payload["windows"], start=1):
            times = np.asarray(window["times"], dtype=float)
            self.assertGreaterEqual(len(times), MIN_POINTS, f"窗口 {index} 少于 {MIN_POINTS} 个点")

            matched = pd.DataFrame({"time_key": np.round(times, 8)}).merge(
                self.good_quality.assign(time_key=self.good_quality["time_jd"].round(8))[["time_key", "frame_quality"]],
                on="time_key",
                how="left",
                validate="one_to_one",
            )
            self.assertFalse(matched["frame_quality"].isna().any(), f"窗口 {index} 包含不存在于输入中的时间点")

            if len(times) > 1:
                self.assertTrue(
                    np.all(np.diff(times) <= gap_days + 1e-12),
                    f"窗口 {index} 内存在超过 90 秒的 gap，应拆分为新窗口",
                )

            if previous_end_time is not None:
                self.assertGreater(
                    times[0] - previous_end_time,
                    gap_days,
                    f"窗口 {index - 1} 与窗口 {index} 之间的 gap 不足 90 秒，不应拆分",
                )
            previous_end_time = times[-1]

    def test_window_structure_and_stats(self):
        payload = self.load_output()
        expected_required = {
            "window_id",
            "start_time",
            "end_time",
            "n_points",
            "times",
            "normalized_flux",
            "mean_flux",
            "median_flux",
            "std_flux",
        }
        for index, window in enumerate(payload["windows"], start=1):
            self.assertTrue(expected_required.issubset(window), f"窗口 {index} 缺少必需字段")
            self.assertEqual(window["window_id"], index, "window_id 必须从 1 开始递增")

            times = window["times"]
            flux = window["normalized_flux"]
            self.assertEqual(len(times), window["n_points"], "n_points 与 times 长度不一致")
            self.assertEqual(len(flux), window["n_points"], "n_points 与 normalized_flux 长度不一致")
            self.assertTrue(all(t2 > t1 for t1, t2 in zip(times, times[1:])), "times 必须严格升序")
            self.assertAlmostEqual(window["start_time"], times[0], places=8)
            self.assertAlmostEqual(window["end_time"], times[-1], places=8)

            arr = np.asarray(flux, dtype=float)
            self.assertAlmostEqual(window["mean_flux"], float(arr.mean()), places=6)
            self.assertAlmostEqual(window["median_flux"], float(np.median(arr)), places=6)
            self.assertAlmostEqual(window["std_flux"], float(arr.std(ddof=0)), places=6)

    def test_windows_are_ordered_and_non_overlapping(self):
        payload = self.load_output()
        starts = [window["start_time"] for window in payload["windows"]]
        self.assertEqual(starts, sorted(starts), "windows 必须按时间顺序输出")
        for left, right in zip(payload["windows"], payload["windows"][1:]):
            self.assertLess(left["end_time"], right["start_time"], "相邻窗口不应重叠")

    def test_normalization_reduces_slow_drift(self):
        payload = self.load_output()
        source_rows = self.good_quality.copy()
        source_rows["time_key"] = source_rows["time_jd"].round(8)

        for window in payload["windows"]:
            out = pd.DataFrame(
                {
                    "time_key": np.round(window["times"], 8),
                    "normalized_flux": window["normalized_flux"],
                }
            )
            merged = out.merge(source_rows[["time_key", "rel_flux"]], on="time_key", how="left", validate="one_to_one")
            self.assertFalse(merged["rel_flux"].isna().any(), "输出窗口包含不存在于输入中的时间点")

            raw_swing = float(np.ptp(rolling_median(merged["rel_flux"], 11)))
            norm_swing = float(np.ptp(rolling_median(merged["normalized_flux"], 11)))
            self.assertLessEqual(norm_swing, raw_swing * 0.4 + 1e-9, "慢漂移压低幅度不足 60%")
            self.assertGreaterEqual(window["median_flux"], 0.995, "median_flux 过低")
            self.assertLessEqual(window["median_flux"], 1.005, "median_flux 过高")

    def test_obvious_spikes_are_removed(self):
        payload = self.load_output()
        all_flux = np.concatenate([np.asarray(window["normalized_flux"], dtype=float) for window in payload["windows"]])
        self.assertLess(all_flux.max(), 1.02, "结果里仍保留明显过高的尖峰")
        self.assertGreater(all_flux.min(), 0.97, "结果里仍保留明显过低的异常点")


if __name__ == "__main__":
    unittest.main()
