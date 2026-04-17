import csv
import os


def test_outputs() -> None:
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
    output_path = os.path.join(workspace_root, "output", "summary.csv")
    assert os.path.exists(output_path), f"缺少输出文件: {output_path}"

    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        actual = list(reader)

    expected = [
        {
            "object_id": "A-01",
            "flux_mjy": "1234.000",
            "luminosity_proxy": "123.4000",
            "quality_flag": "ok",
        },
        {
            "object_id": "A-02",
            "flux_mjy": "500.000",
            "luminosity_proxy": "200.0000",
            "quality_flag": "ok",
        },
        {
            "object_id": "A-03",
            "flux_mjy": "",
            "luminosity_proxy": "",
            "quality_flag": "ok",
        },
        {
            "object_id": "A-04",
            "flux_mjy": "2000.000",
            "luminosity_proxy": "",
            "quality_flag": "review",
        },
    ]

    expected_headers = ["object_id", "flux_mjy", "luminosity_proxy", "quality_flag"]
    assert reader.fieldnames == expected_headers, f"输出列不匹配: {reader.fieldnames}"
    assert actual == expected, f"输出内容不匹配.\nactual={actual}\nexpected={expected}"
