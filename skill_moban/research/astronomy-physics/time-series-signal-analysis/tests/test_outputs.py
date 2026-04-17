import json
import math
import os


def test_outputs() -> None:
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
    output_path = os.path.join(workspace_root, "output", "signal_report.json")
    assert os.path.exists(output_path), f"缺少输出文件: {output_path}"

    with open(output_path, "r", encoding="utf-8") as f:
        actual = json.load(f)

    expected_keys = {
        "series_id",
        "n_points",
        "mean_flux",
        "std_flux",
        "min_flux",
        "max_flux",
        "top_peak_times",
    }
    assert set(actual.keys()) == expected_keys, f"JSON 字段不匹配: {sorted(actual.keys())}"

    assert actual["series_id"] == "template-series-01"
    assert actual["n_points"] == 5
    assert math.isclose(actual["mean_flux"], 1.08, rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(actual["std_flux"], 0.248193, rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(actual["min_flux"], 0.8, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(actual["max_flux"], 1.5, rel_tol=0.0, abs_tol=1e-9)

    peaks = actual["top_peak_times"]
    assert isinstance(peaks, list) and len(peaks) == 2, f"top_peak_times 格式错误: {peaks}"
    assert peaks == [4.0, 2.0], f"峰值时间不匹配: {peaks}"
