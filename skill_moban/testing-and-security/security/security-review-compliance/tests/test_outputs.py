import csv
import os


def test_outputs() -> None:
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
    output_path = os.path.join(workspace_root, "output", "review_matrix.csv")
    assert os.path.exists(output_path), f"缺少输出文件: {output_path}"

    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        actual = list(reader)
        headers = reader.fieldnames

    expected_headers = [
        "component",
        "critical_count",
        "high_count",
        "medium_count",
        "low_count",
        "gdpr_flag",
        "status",
    ]
    assert headers == expected_headers, f"输出列不匹配: {headers}"

    expected = [
        {
            "component": "api-gateway",
            "critical_count": "1",
            "high_count": "0",
            "medium_count": "0",
            "low_count": "1",
            "gdpr_flag": "false",
            "status": "fail",
        },
        {
            "component": "billing-service",
            "critical_count": "0",
            "high_count": "2",
            "medium_count": "0",
            "low_count": "0",
            "gdpr_flag": "false",
            "status": "fail",
        },
        {
            "component": "profile-service",
            "critical_count": "0",
            "high_count": "0",
            "medium_count": "1",
            "low_count": "0",
            "gdpr_flag": "true",
            "status": "fail",
        },
        {
            "component": "reporting-worker",
            "critical_count": "0",
            "high_count": "0",
            "medium_count": "2",
            "low_count": "0",
            "gdpr_flag": "false",
            "status": "warn",
        },
        {
            "component": "search-ui",
            "critical_count": "0",
            "high_count": "1",
            "medium_count": "0",
            "low_count": "0",
            "gdpr_flag": "false",
            "status": "warn",
        },
        {
            "component": "static-site",
            "critical_count": "0",
            "high_count": "0",
            "medium_count": "0",
            "low_count": "1",
            "gdpr_flag": "false",
            "status": "pass",
        },
    ]
    assert actual == expected, f"输出内容不匹配.\nactual={actual}\nexpected={expected}"


if __name__ == "__main__":
    test_outputs()
