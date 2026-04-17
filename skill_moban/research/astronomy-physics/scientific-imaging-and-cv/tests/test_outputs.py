import json
import math
import os


def test_outputs() -> None:
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
    output_path = os.path.join(workspace_root, "output", "image_report.json")
    assert os.path.exists(output_path), f"缺少输出文件: {output_path}"

    with open(output_path, "r", encoding="utf-8") as f:
        actual = json.load(f)

    assert set(actual.keys()) == {"image_count", "mean_normalized_brightness", "records"}
    assert actual["image_count"] == 3
    assert math.isclose(actual["mean_normalized_brightness"], 0.4476, rel_tol=0.0, abs_tol=1e-6)

    records = actual["records"]
    assert isinstance(records, list) and len(records) == 3

    expected = [
        {"image_id": "IMG-01", "normalized_brightness": 0.4395, "quality_tag": "sharp"},
        {"image_id": "IMG-02", "normalized_brightness": 0.2197, "quality_tag": "soft"},
        {"image_id": "IMG-03", "normalized_brightness": 0.6836, "quality_tag": "sharp"},
    ]
    assert records == expected, f"records 不匹配.\nactual={records}\nexpected={expected}"
