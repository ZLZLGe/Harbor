import json
import os
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/pipeline_choice.json"))
EXPECTED_KEYS = {
    "selected_pipeline_id",
    "orbital_period_days",
    "estimated_transit_depth_ppt",
    "evidence",
}
EXPECTED_PIPELINE = "pipeline_b"
EXPECTED_PERIOD = 6.28431
PERIOD_TOLERANCE = 0.04
EXPECTED_DEPTH_PPT = 1.93
DEPTH_TOLERANCE = 0.7


def load_output():
    assert OUTPUT_PATH.exists(), "缺少 /root/pipeline_choice.json"
    with OUTPUT_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少 /root/pipeline_choice.json"


def test_schema_and_types():
    payload = load_output()
    assert isinstance(payload, dict), "输出必须是 JSON 对象"
    assert set(payload.keys()) == EXPECTED_KEYS, "JSON 键必须且只包含 selected_pipeline_id、orbital_period_days、estimated_transit_depth_ppt、evidence"
    assert isinstance(payload["selected_pipeline_id"], str), "selected_pipeline_id 必须是字符串"
    assert isinstance(payload["orbital_period_days"], (int, float)), "orbital_period_days 必须是数值"
    assert isinstance(payload["estimated_transit_depth_ppt"], (int, float)), "estimated_transit_depth_ppt 必须是数值"
    assert isinstance(payload["evidence"], list), "evidence 必须是字符串数组"


def test_choice_is_correct_pipeline():
    payload = load_output()
    assert payload["selected_pipeline_id"] in {"pipeline_a", "pipeline_b", "pipeline_c"}, "selected_pipeline_id 不在允许范围内"
    assert payload["selected_pipeline_id"] == EXPECTED_PIPELINE, "选出的保留分支不正确"


def test_period_and_depth_values():
    payload = load_output()
    period = float(payload["orbital_period_days"])
    depth = float(payload["estimated_transit_depth_ppt"])

    assert abs(period - round(period, 5)) < 1e-10, "orbital_period_days 必须四舍五入到 5 位小数"
    assert abs(depth - round(depth, 2)) < 1e-10, "estimated_transit_depth_ppt 必须四舍五入到 2 位小数"
    assert abs(period - EXPECTED_PERIOD) <= PERIOD_TOLERANCE, "orbital_period_days 与正确分支中的凌星周期不符"
    assert abs(depth - EXPECTED_DEPTH_PPT) <= DEPTH_TOLERANCE, "estimated_transit_depth_ppt 与正确分支中的浅凌星深度不符"
    assert 1.2 <= depth <= 3.2, "estimated_transit_depth_ppt 应落在浅凌星的合理范围内"


def test_evidence_contract():
    payload = load_output()
    evidence = payload["evidence"]

    assert len(evidence) == 2, "evidence 必须恰好包含 2 条字符串"
    assert all(isinstance(item, str) and item.strip() for item in evidence), "evidence 中每一项都必须是非空字符串"

    first = evidence[0]
    second = evidence[1]
    combined = "\n".join(evidence)

    assert payload["selected_pipeline_id"] in combined, "evidence 需要明确点名所选分支"
    assert any(name in second for name in ["pipeline_a", "pipeline_c"]), "第 2 条 evidence 需要点名至少一条未选分支"
    assert first != second, "两条 evidence 应分别覆盖入选理由和未选分支问题"
    assert len(first.strip()) >= 12, "第 1 条 evidence 需要给出明确的入选理由"
    assert len(second.strip()) >= 12, "第 2 条 evidence 需要给出明确的未选原因"
