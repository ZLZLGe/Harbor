from __future__ import annotations

import re

from conftest import OUTPUT_PATH, brand_tokens, contains_number_variant, expected_summary, read_output, snapshot, soup, visible_text


def test_a_output_exists_and_is_self_contained_html() -> None:
    assert OUTPUT_PATH.exists(), OUTPUT_PATH
    assert OUTPUT_PATH.stat().st_size > 12_000
    html = read_output()
    doc = soup()
    assert doc.html is not None
    assert doc.find("style") is not None
    assert doc.find("script") is not None
    forbidden_runtime_patterns = [
        r"<script[^>]+src=",
        r"<link[^>]+href=['\"]https?://",
        r"<img[^>]+src=['\"]https?://",
        r"\bfetch\s*\(",
        r"XMLHttpRequest",
        r"http://127\.0\.0\.1:8111",
        r"https?://cdn\.",
    ]
    for pattern in forbidden_runtime_patterns:
        assert not re.search(pattern, html, flags=re.IGNORECASE), pattern


def test_b_slide_deck_structure_and_required_story_beats() -> None:
    doc = soup()
    sections = doc.find_all("section")
    assert 8 <= len(sections) <= 10
    assert sum(1 for section in sections if section.find(re.compile("^h[1-3]$"))) >= 8
    text = visible_text()
    required_groups = [
        ("executive", "summary", "复盘", "摘要"),
        ("key", "metric", "kpi", "指标"),
        ("zone", "area", "区域"),
        ("weather", "天气", "rain", "wind"),
        ("complaint", "customer", "客诉", "投诉"),
        ("recommend", "roadmap", "next quarter", "q2", "建议", "路线"),
    ]
    missing = [group for group in required_groups if not any(phrase in text for phrase in group)]
    assert not missing, missing


def test_c_deck_is_grounded_in_all_business_sources() -> None:
    snap = snapshot()
    summary = expected_summary()
    text = visible_text()
    assert snap["city"].lower() in text
    assert snap["quarter"].lower() in text
    assert "harborloop" in text
    key_metric_hits = [
        contains_number_variant(text, snap["quarter_totals"]["trips"]),
        contains_number_variant(text, snap["fleet"]["active_vehicles"]),
        contains_number_variant(text, snap["quarter_totals"]["service_uptime_pct"], percent=True),
        contains_number_variant(text, snap["quarter_totals"]["customer_satisfaction_pct"], percent=True),
        "142" in text,
        "3.4" in text or "3420" in text or "3,420" in text,
    ]
    assert sum(1 for hit in key_metric_hits if hit) >= 3
    for zone in summary["shortage_rank"][:3]:
        assert zone.lower() in text
    theme_aliases = {
        "morning vehicle shortage": ("morning", "shortage", "vehicle", "campus", "缺车", "短缺"),
        "empty docks at ferry arrivals": ("empty", "dock", "ferry", "waterfront", "码头", "渡轮"),
        "weather-related unavailable vehicles": ("weather", "unavailable", "rain", "天气", "不可用"),
    }
    theme_hits = 0
    for theme in summary["top_themes"]:
        aliases = theme_aliases.get(theme, tuple(theme.lower().split()))
        if sum(1 for token in aliases if token in text) >= 2:
            theme_hits += 1
    assert theme_hits >= 2
    for event in summary["weather"]["events"][:2]:
        assert event["label"].split()[0].lower() in text or event["start_date"][5:7] in text
        event_terms = [
            event["event_type"].lower().split()[0],
            str(event["trip_change_pct"]),
            str(event["availability_change_pct"]),
            *[zone.lower() for zone in event["affected_zones"]],
        ]
        assert sum(1 for term in event_terms if term in text) >= 2, event
    service_terms = ["critical", "high", "medium", "watch", "priority", "服务", "分区", "优先"]
    assert sum(1 for term in service_terms if term in text) >= 2


def test_d_brand_tokens_and_visualization_markup_are_present() -> None:
    html = read_output().lower()
    colors = [value.lower() for value in brand_tokens()["colors"].values()]
    used_colors = [color for color in colors if color in html]
    assert len(used_colors) >= 4, used_colors
    doc = soup()
    visual_nodes = doc.select(
        "svg, canvas, [class*='chart'], [class*='graph'], [class*='bar'], "
        "[class*='matrix'], [data-chart], [data-visualization]"
    )
    assert len(visual_nodes) >= 3
    metric_like = re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:%|k|m|usd|vehicles|trips)?\b", visible_text())
    assert len(metric_like) >= 10


def test_e_recommendations_are_actionable_not_placeholder_copy() -> None:
    text = visible_text()
    planning_terms = ["recommend", "next quarter", "roadmap", "q2", "建议", "路线", "下季度"]
    assert sum(text.count(term) for term in planning_terms) >= 1
    action_terms = ["rebalance", "battery", "ferry", "campus", "weather", "staff", "corral", "dock", "补位", "电池", "渡轮", "天气", "调度", "停放"]
    assert sum(1 for term in action_terms if term in text) >= 5
    placeholder_terms = ["lorem ipsum", "todo", "placeholder", "sample text", "insert chart"]
    assert not any(term in text for term in placeholder_terms)
