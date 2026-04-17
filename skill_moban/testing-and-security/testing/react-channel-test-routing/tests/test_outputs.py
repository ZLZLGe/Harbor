import csv
import os


def test_outputs() -> None:
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
    output_path = os.path.join(workspace_root, "output", "react_test_plan.csv")
    assert os.path.exists(output_path), f"缺少输出文件: {output_path}"

    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        actual = list(reader)
        headers = reader.fieldnames

    expected_headers = [
        "case_id",
        "command",
        "gate_strategy",
        "flag_check",
        "expected_channel_state",
        "notes",
    ]
    assert headers == expected_headers, f"输出列不匹配: {headers}"

    expected = [
        {
            "case_id": "C001",
            "command": "yarn test --silent --no-watchman ReactDOMFizzServer",
            "gate_strategy": "none",
            "flag_check": "not-needed",
            "expected_channel_state": "source-default",
            "notes": "baseline route",
        },
        {
            "case_id": "C002",
            "command": "yarn test -r=experimental --silent --no-watchman ReactDeferredValue",
            "gate_strategy": "gate()",
            "flag_check": "enableAsyncActions=experimental-on",
            "expected_channel_state": "experimental-enabled",
            "notes": "assert both flag branches",
        },
        {
            "case_id": "C003",
            "command": "yarn test-www --silent --no-watchman ReactFlightDOM",
            "gate_strategy": "@gate enableFlight",
            "flag_check": "enableFlight=variant:true",
            "expected_channel_state": "www-modern-variant-true",
            "notes": "skip unless flag enabled",
        },
        {
            "case_id": "C004",
            "command": "yarn test-www --variant=false --silent --no-watchman ReactCache",
            "gate_strategy": "gate()",
            "flag_check": "enableCache=variant:false",
            "expected_channel_state": "www-modern-variant-false",
            "notes": "assert both flag branches",
        },
        {
            "case_id": "C005",
            "command": "yarn test-stable --silent --no-watchman ReactDOMHydration",
            "gate_strategy": "none",
            "flag_check": "not-needed",
            "expected_channel_state": "stable-release",
            "notes": "baseline route",
        },
        {
            "case_id": "C006",
            "command": "yarn test-classic --silent --no-watchman ReactLegacyContext",
            "gate_strategy": "@gate enableLegacyContext",
            "flag_check": "enableLegacyContext=classic-default",
            "expected_channel_state": "www-classic",
            "notes": "skip unless flag enabled",
        },
    ]
    assert actual == expected, f"输出内容不匹配.\nactual={actual}\nexpected={expected}"

    case_ids = [row["case_id"] for row in actual]
    assert case_ids == sorted(case_ids), f"case_id 未升序排序: {case_ids}"

    forbidden = {"", "null", "None", "nan", "NaN"}
    for row in actual:
        for key, value in row.items():
            assert value not in forbidden, f"{key} 包含非法空值表示: {value!r}"


if __name__ == "__main__":
    test_outputs()
