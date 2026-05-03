from __future__ import annotations

from common import (
    CAMPAIGN_SUMMARY_PATH,
    CONSTRAINTS,
    GAPS_PATH,
    LINKEDIN_PATH,
    NEWSLETTER_PATH,
    RED_FLAGS,
    SOURCE_INDEX,
    SOURCE_MAP_PATH,
    X_THREAD_PATH,
    get_ref_text,
    h2_count,
    load_json,
    paragraph_count,
    thread_lines,
    unique_words,
    word_count,
)


def test_required_output_files_exist_and_parse() -> None:
    assert CAMPAIGN_SUMMARY_PATH.exists(), "Missing /root/output/campaign_summary.md"
    assert X_THREAD_PATH.exists(), "Missing /root/output/x_thread.md"
    assert LINKEDIN_PATH.exists(), "Missing /root/output/linkedin_post.md"
    assert NEWSLETTER_PATH.exists(), "Missing /root/output/newsletter_draft.md"
    assert SOURCE_MAP_PATH.exists(), "Missing /root/output/source_map.json"
    assert GAPS_PATH.exists(), "Missing /root/output/publish_gaps.json"
    assert load_json(SOURCE_MAP_PATH)
    assert load_json(GAPS_PATH)


def test_campaign_summary_has_required_shape() -> None:
    text = CAMPAIGN_SUMMARY_PATH.read_text(encoding="utf-8").strip()
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    assert len(lines) >= 4, "campaign_summary.md must contain one summary line plus three channel lines"
    assert not lines[0].startswith("- "), "First line must be the summary sentence"
    bullet_lines = [line for line in lines[1:] if line.startswith("- ")]
    assert len(bullet_lines) == 3, "campaign_summary.md must contain exactly three channel bullets"
    lowered = "\n".join(bullet_lines).lower()
    assert "x" in lowered
    assert "linkedin" in lowered
    assert "newsletter" in lowered


def test_source_map_is_grounded_and_complete() -> None:
    payload = load_json(SOURCE_MAP_PATH)
    assert payload["anchor_asset"] == "anchor_article.md"
    assert isinstance(payload["shared_limits"], list) and payload["shared_limits"]
    for required_limit in CONSTRAINTS["required_shared_limits"]:
        assert required_limit in payload["shared_limits"], f"shared limit missing: {required_limit}"

    entries = {item["file"]: item for item in payload["deliverables"]}
    assert set(entries) == {"x_thread.md", "linkedin_post.md", "newsletter_draft.md"}

    focus_values = []
    allowed_paths = {doc["path"] for doc in SOURCE_INDEX["docs"]}
    for spec in CONSTRAINTS["deliverables"]:
        entry = entries[spec["file"]]
        assert entry["audience"].strip(), f"audience missing for {spec['file']}"
        assert entry["content_focus"].strip(), f"content_focus missing for {spec['file']}"
        focus_values.append(entry["content_focus"].strip().lower())
        refs = entry["source_refs"]
        assert len(refs) >= spec["min_source_refs"], f"{spec['file']} has too few source refs"
        distinct_paths = {ref.split("#", 1)[0] for ref in refs}
        assert len(distinct_paths) >= spec["min_distinct_files"], f"{spec['file']} cites too few distinct files"
        for ref in refs:
            rel_path = ref.split("#", 1)[0]
            assert rel_path in allowed_paths, f"{spec['file']} cites unknown source path {rel_path}"
            excerpt = get_ref_text(ref)
            assert excerpt.strip(), f"{spec['file']} cites empty source range {ref}"

    assert len(set(focus_values)) == 3, "Each deliverable must keep a distinct channel emphasis"


def test_channel_specific_structure_and_word_counts() -> None:
    x_text = X_THREAD_PATH.read_text(encoding="utf-8").strip()
    thread = thread_lines(x_text)
    assert 5 <= len(thread) <= 7, "X thread must contain 5 to 7 numbered lines"
    assert thread[0].startswith("1/"), "X thread must start at 1/"
    for idx, line in enumerate(thread, start=1):
        assert line.startswith(f"{idx}/"), f"X thread numbering gap at line {idx}"

    linkedin_text = LINKEDIN_PATH.read_text(encoding="utf-8")
    linkedin_words = word_count(linkedin_text)
    assert 180 <= linkedin_words <= 320, "LinkedIn post word count is out of range"
    assert paragraph_count(linkedin_text) <= 6, "LinkedIn post has too many paragraphs"

    newsletter_text = NEWSLETTER_PATH.read_text(encoding="utf-8")
    lines = newsletter_text.splitlines()
    assert len(lines) >= 2
    assert lines[0].startswith("Subject:"), "newsletter_draft.md must start with Subject:"
    assert lines[1].startswith("Preview:"), "newsletter_draft.md second line must start with Preview:"
    newsletter_words = word_count(newsletter_text)
    assert 350 <= newsletter_words <= 550, "Newsletter word count is out of range"
    assert h2_count(newsletter_text) >= 3, "Newsletter must contain at least three H2 sections"


def test_assets_reflect_constraints_and_source_grounding() -> None:
    payload = load_json(SOURCE_MAP_PATH)
    entries = {item["file"]: item for item in payload["deliverables"]}

    for spec in CONSTRAINTS["deliverables"]:
        file_name = spec["file"]
        if file_name == "x_thread.md":
            text = X_THREAD_PATH.read_text(encoding="utf-8")
        elif file_name == "linkedin_post.md":
            text = LINKEDIN_PATH.read_text(encoding="utf-8")
        else:
            text = NEWSLETTER_PATH.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in RED_FLAGS:
            assert phrase not in lowered, f"{file_name} contains blocked phrase: {phrase}"
        hits = sum(1 for keyword in spec["required_keywords"] if keyword in lowered)
        assert hits >= 3, f"{file_name} does not reflect enough required channel keywords"

        source_text = "\n".join(get_ref_text(ref) for ref in entries[file_name]["source_refs"])
        overlap = unique_words(source_text) & unique_words(text)
        assert len(overlap) >= 10, f"{file_name} does not appear grounded in its cited source ranges"


def test_outputs_are_not_cross_channel_copies() -> None:
    texts = {
        "x_thread.md": unique_words(X_THREAD_PATH.read_text(encoding="utf-8")),
        "linkedin_post.md": unique_words(LINKEDIN_PATH.read_text(encoding="utf-8")),
        "newsletter_draft.md": unique_words(NEWSLETTER_PATH.read_text(encoding="utf-8")),
    }
    names = sorted(texts)
    for idx, left in enumerate(names):
        for right in names[idx + 1 :]:
            overlap = texts[left] & texts[right]
            union = texts[left] | texts[right]
            assert union, "empty deliverable text"
            assert len(overlap) / len(union) < 0.7, f"{left} and {right} overlap too much"


def test_publish_gaps_cover_release_followups() -> None:
    payload = load_json(GAPS_PATH)
    gaps = payload["gaps"]
    assert isinstance(gaps, list) and len(gaps) >= 3, "publish_gaps.json must include at least three gaps"
    lowered = " ".join(
        f"{item['topic']} {item['why_it_matters']} {item['needed_from_team']}".lower()
        for item in gaps
    )
    for keyword in CONSTRAINTS["publish_gap_topics"]:
        parts = keyword.replace("-", " ").split()
        assert any(part in lowered for part in parts), f"publish gaps must cover {keyword}"
