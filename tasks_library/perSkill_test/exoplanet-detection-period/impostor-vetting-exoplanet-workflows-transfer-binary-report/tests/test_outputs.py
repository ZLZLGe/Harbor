import re
from pathlib import Path


OUTPUT_PATH = Path("/root/vetting_report.md")
EXPECTED_PERIOD = 3.21570
PERIOD_TOLERANCE = 0.02


def read_report() -> str:
    assert OUTPUT_PATH.exists(), "缺少 /root/vetting_report.md"
    return OUTPUT_PATH.read_text(encoding="utf-8")


def parse_numeric_field(report: str, field_name: str) -> tuple[float, str]:
    prefix = f"- {field_name}: "
    for line in report.splitlines():
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            return float(value), value
    raise AssertionError(f"缺少字段 {field_name}")


def parse_text_field(report: str, field_name: str) -> str:
    prefix = f"- {field_name}: "
    for line in report.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    raise AssertionError(f"缺少字段 {field_name}")


def evidence_lines(report: str) -> list[str]:
    parts = report.split("## Evidence", 1)
    assert len(parts) == 2, "缺少 ## Evidence 小节"
    lines = [line for line in parts[1].splitlines() if line.startswith("- ")]
    assert lines, "## Evidence 小节下缺少项目符号"
    return lines


def test_report_exists():
    assert OUTPUT_PATH.exists(), "缺少 /root/vetting_report.md"


def test_required_fields_and_rounding():
    report = read_report()
    period, period_text = parse_numeric_field(report, "best_period_days")
    odd_depth, odd_text = parse_numeric_field(report, "odd_event_depth_ppt")
    even_depth, even_text = parse_numeric_field(report, "even_event_depth_ppt")

    assert "." in period_text and len(period_text.split(".")[1]) == 5, "best_period_days 必须保留 5 位小数"
    assert "." in odd_text and len(odd_text.split(".")[1]) == 2, "odd_event_depth_ppt 必须保留 2 位小数"
    assert "." in even_text and len(even_text.split(".")[1]) == 2, "even_event_depth_ppt 必须保留 2 位小数"

    assert period > 0.0, "best_period_days 必须为正数"
    assert odd_depth > 0.0, "odd_event_depth_ppt 必须为正数"
    assert even_depth > 0.0, "even_event_depth_ppt 必须为正数"


def test_period_and_verdict_semantics():
    report = read_report()
    period, _ = parse_numeric_field(report, "best_period_days")
    verdict = parse_text_field(report, "verdict")

    assert abs(period - EXPECTED_PERIOD) <= PERIOD_TOLERANCE, "最佳候选周期不在允许误差范围内"
    assert verdict in {"行星", "食双星"}, "verdict 必须是 行星 或 食双星"
    assert verdict == "食双星", "该候选应被判定为食双星"


def test_odd_even_mismatch_supports_binary_vetting():
    report = read_report()
    odd_depth, _ = parse_numeric_field(report, "odd_event_depth_ppt")
    even_depth, _ = parse_numeric_field(report, "even_event_depth_ppt")

    assert 5.0 <= odd_depth <= 15.0, "odd_event_depth_ppt 与数据不符"
    assert 18.0 <= even_depth <= 32.0, "even_event_depth_ppt 与数据不符"
    assert even_depth - odd_depth >= 8.0, "奇偶事件深度差异不足以支持该数据中的食双星判定"


def test_evidence_section_present():
    report = read_report()
    lines = evidence_lines(report)
    assert len(lines) >= 2, "## Evidence 小节至少需要两条项目符号"
    assert "食双星" in report, "报告中应明确给出食双星判定"
