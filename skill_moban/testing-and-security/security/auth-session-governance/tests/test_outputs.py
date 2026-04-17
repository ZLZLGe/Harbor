import json
import os
from collections import OrderedDict
from pathlib import Path


EXPECTED = OrderedDict(
    [
        (
            "summary",
            OrderedDict(
                [
                    ("total_flows", 5),
                    ("blocked_flows", 3),
                ]
            ),
        ),
        (
            "flows",
            [
                OrderedDict(
                    [
                        ("flow_id", "A100"),
                        ("status", "pass"),
                        ("risk_level", "low"),
                        ("risk_score", 0),
                        ("reasons", []),
                    ]
                ),
                OrderedDict(
                    [
                        ("flow_id", "A200"),
                        ("status", "review"),
                        ("risk_level", "medium"),
                        ("risk_score", 30),
                        ("reasons", ["rotation_too_slow", "bruteforce_risk", "session_ttl_too_long"]),
                    ]
                ),
                OrderedDict(
                    [
                        ("flow_id", "A300"),
                        ("status", "blocked"),
                        ("risk_level", "medium"),
                        ("risk_score", 40),
                        ("reasons", ["mfa_missing"]),
                    ]
                ),
                OrderedDict(
                    [
                        ("flow_id", "A400"),
                        ("status", "blocked"),
                        ("risk_level", "medium"),
                        ("risk_score", 40),
                        ("reasons", ["cookie_not_secure", "cookie_not_httponly"]),
                    ]
                ),
                OrderedDict(
                    [
                        ("flow_id", "A500"),
                        ("status", "blocked"),
                        ("risk_level", "medium"),
                        ("risk_score", 40),
                        ("reasons", ["cookie_not_httponly", "rotation_too_slow", "bruteforce_risk"]),
                    ]
                ),
            ],
        ),
    ]
)


EXPECTED_FLOW_KEYS = ["flow_id", "status", "risk_level", "risk_score", "reasons"]
EXPECTED_ROOT_KEYS = ["summary", "flows"]
EXPECTED_SUMMARY_KEYS = ["total_flows", "blocked_flows"]


def main() -> None:
    workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
    output_path = workspace_root / "output" / "auth_gate.json"
    assert output_path.exists(), f"缺少输出文件: {output_path}"

    with output_path.open("r", encoding="utf-8") as f:
        payload = json.load(f, object_pairs_hook=OrderedDict)

    assert list(payload.keys()) == EXPECTED_ROOT_KEYS, f"根字段顺序不匹配: {list(payload.keys())}"
    assert list(payload["summary"].keys()) == EXPECTED_SUMMARY_KEYS, (
        f"summary 字段顺序不匹配: {list(payload['summary'].keys())}"
    )

    actual_flows = payload["flows"]
    assert isinstance(actual_flows, list), "flows 必须为数组"
    assert len(actual_flows) == 5, f"flows 数量不匹配: {len(actual_flows)}"

    for flow in actual_flows:
        assert list(flow.keys()) == EXPECTED_FLOW_KEYS, f"flow 字段顺序不匹配: {list(flow.keys())}"

    assert payload == EXPECTED, f"输出内容不匹配.\nactual={payload}\nexpected={EXPECTED}"


if __name__ == "__main__":
    main()
