import csv
import os


def test_outputs() -> None:
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
    output_path = os.path.join(workspace_root, "output", "event_summary.csv")
    assert os.path.exists(output_path), f"缺少输出文件: {output_path}"

    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        actual = list(reader)
        headers = reader.fieldnames

    expected_headers = [
        "event_type",
        "event_count",
        "avg_duration_hours",
        "max_severity",
        "latest_start_time",
    ]
    expected_rows = [
        {
            "event_type": "marine_warning",
            "event_count": "1",
            "avg_duration_hours": "2.000",
            "max_severity": "1",
            "latest_start_time": "2026-01-01T02:00:00",
        },
        {
            "event_type": "seismic_notice",
            "event_count": "2",
            "avg_duration_hours": "2.250",
            "max_severity": "5",
            "latest_start_time": "2026-01-04T05:00:00",
        },
        {
            "event_type": "solar_alert",
            "event_count": "2",
            "avg_duration_hours": "2.750",
            "max_severity": "4",
            "latest_start_time": "2026-01-02T09:30:00",
        },
    ]

    assert headers == expected_headers, f"输出列不匹配: {headers}"
    assert actual == expected_rows, f"输出内容不匹配.\nactual={actual}\nexpected={expected_rows}"
