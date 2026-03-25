import unittest
from pathlib import Path

import pandas as pd


INPUT_PATH = Path("/root/data/tess_s028_quicklook.csv")
OUTPUT_PATH = Path("/root/transit_ready_lightcurve.csv")
GOOD_ROW_COUNT = 838


class TransitReadyLightCurveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = pd.read_csv(INPUT_PATH)

    def load_output(self):
        self.assertTrue(OUTPUT_PATH.exists(), "缺少 /root/transit_ready_lightcurve.csv")
        return pd.read_csv(OUTPUT_PATH)

    def test_output_exists(self):
        self.assertTrue(OUTPUT_PATH.exists(), "缺少 /root/transit_ready_lightcurve.csv")

    def test_required_columns_exist(self):
        output = self.load_output()
        required = {"time", "flat_flux", "flux_err"}
        self.assertTrue(required.issubset(output.columns), f"输出缺少必需列: {required - set(output.columns)}")

    def test_output_is_sorted_and_uses_good_quality_rows(self):
        output = self.load_output()
        time = output["time"]
        self.assertTrue(time.is_monotonic_increasing, "time 列必须升序排列")
        self.assertEqual(time.nunique(), len(time), "输出中不应出现重复 time")

        source = self.source.copy()
        source["time_key"] = source["time"].round(8)
        output = output.copy()
        output["time_key"] = output["time"].round(8)

        merged = output.merge(
            source[["time_key", "quality", "flux_err"]],
            on="time_key",
            how="left",
            validate="one_to_one",
        )
        self.assertFalse(merged["quality"].isna().any(), "输出里有 time 不存在于输入数据")
        self.assertTrue((merged["quality"] == 0).all(), "输出里仍然包含 quality 非零的坏点")

    def test_flux_err_matches_retained_points(self):
        output = self.load_output()
        source = self.source.copy()
        source["time_key"] = source["time"].round(8)
        output = output.copy()
        output["time_key"] = output["time"].round(8)

        merged = output.merge(
            source[["time_key", "flux_err"]],
            on="time_key",
            how="left",
            validate="one_to_one",
            suffixes=("_out", "_src"),
        )
        diff = (merged["flux_err_out"] - merged["flux_err_src"]).abs().max()
        self.assertLess(diff, 1e-10, "flux_err 必须对应最终保留下来的观测点")

    def test_row_count_stays_close_to_original_cadence(self):
        output = self.load_output()
        self.assertEqual(int((self.source["quality"] == 0).sum()), GOOD_ROW_COUNT, "输入资产统计与任务说明不一致")
        out_rows = len(output)
        self.assertGreaterEqual(out_rows, 820, "不应过度删点或重采样")
        self.assertLess(out_rows, GOOD_ROW_COUNT, "明显离群点应被剔除，不能把所有 good rows 原样导出")

    def test_curve_is_flattened(self):
        output = self.load_output()
        rolling = output["flat_flux"].rolling(window=97, center=True, min_periods=1).median()
        center = rolling.iloc[48:-48]
        self.assertFalse(center.empty, "输出行数不足，无法形成稳定的预处理结果")
        max_deviation = (center - 1.0).abs().max()
        self.assertLess(max_deviation, 0.0025, "flat_flux 仍保留过强的慢变趋势")

    def test_obvious_outliers_are_gone(self):
        output = self.load_output()
        self.assertGreater(output["flat_flux"].min(), 0.99, "仍存在明显过深的异常点")
        self.assertLess(output["flat_flux"].max(), 1.01, "仍存在明显过高的异常点")

    def test_short_dips_remain_visible(self):
        output = self.load_output()
        self.assertLess(
            output["flat_flux"].quantile(0.02),
            0.9975,
            "不要把真实的短时浅暗化结构一起裁掉",
        )


if __name__ == "__main__":
    unittest.main()
