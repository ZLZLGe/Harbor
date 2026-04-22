import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(os.environ.get("CONTENT_ROOT", "/root"))
PACKAGE_PATH = Path(os.environ.get("PUBLISH_BUNDLE_OUTPUT_PATH", "/root/publish_bundle.json"))
CTA_URL = "https://signalleaf.example.com/studio-waitlist"
PRIMARY_KEYWORD = "content repurposing workflow"
SECONDARY_KEYWORDS = {
    "webinar repurposing",
    "editorial approval workflow",
    "multi-channel content pack",
}
FORBIDDEN_PHRASES = [
    "free plan",
    "free forever",
    "every plan",
    "20+ languages",
    "20 languages",
    "auto-publish",
    "publish everywhere",
    "every social platform",
    "schedule everything",
    "automatic long-form video editing",
    "edit the long-form video",
]


def _run_build() -> tuple[subprocess.CompletedProcess[str], dict]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "build_bundle.py")],
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    payload = {}
    if PACKAGE_PATH.exists():
        payload = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    return completed, payload


def _count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9%+-]+", text))


def _count_hashtags(text: str) -> int:
    return len(re.findall(r"(^|\s)#\w+", text))


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _jaccard(a: str, b: str) -> float:
    set_a = {token for token in _token_set(a) if len(token) >= 4}
    set_b = {token for token in _token_set(b) if len(token) >= 4}
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)


def _contains_positive_unsupported_claim(text: str) -> bool:
    patterns = [
        "free plan",
        "free forever",
        "every plan",
        "20+ languages",
        "20 languages",
        "auto-publish",
        "publish everywhere",
        "every social platform",
        "schedule everything",
        "automatic long-form video editing",
        "edit the long-form video",
    ]
    negations = [
        "not ",
        "do not",
        "does not",
        "don't",
        "doesn't",
        "is not",
        "isn't",
        "no ",
        "without",
        "not part of",
        "not confirmed",
        "not include",
        "not included",
        "not in launch scope",
    ]
    sentences = [segment.strip().lower() for segment in re.split(r"(?<=[.!?])\s+|\n+", text) if segment.strip()]
    for sentence in sentences:
        for phrase in patterns:
            if phrase in sentence:
                if any(neg in sentence for neg in negations):
                    continue
                return True
    return False


def _load_outputs() -> tuple[str, str, dict, dict]:
    blog = (ROOT / "blog_post.md").read_text(encoding="utf-8")
    linkedin = (ROOT / "linkedin_post.md").read_text(encoding="utf-8")
    newsletter = json.loads((ROOT / "newsletter.json").read_text(encoding="utf-8"))
    seo_meta = json.loads((ROOT / "seo_meta.json").read_text(encoding="utf-8"))
    return blog, linkedin, newsletter, seo_meta


def test_build_bundle_succeeds_and_writes_summary():
    completed, payload = _run_build()
    assert completed.returncode == 0, completed.stderr
    assert payload["bundle_id"] == "signalleaf-studio-2-0-launch"
    assert payload["product_name"] == "SignalLeaf Studio 2.0"
    assert payload["launch_date"] == "2026-04-28"
    assert payload["primary_keyword"] == PRIMARY_KEYWORD


def test_required_outputs_exist_and_are_parseable():
    blog, linkedin, newsletter, seo_meta = _load_outputs()
    assert blog.strip()
    assert linkedin.strip()
    assert isinstance(newsletter, dict)
    assert isinstance(seo_meta, dict)
    assert set(newsletter) == {"subject", "preview_text", "body_markdown", "cta_label", "cta_url"}
    assert set(seo_meta) == {"slug", "title", "description", "primary_keyword", "secondary_keywords"}


def test_blog_post_is_publish_ready_and_factually_grounded():
    blog, _, _, _ = _load_outputs()
    blog_lower = blog.lower()
    assert blog.startswith("# ")
    assert _count_words(blog) >= 380
    assert 3 <= blog.count("\n## ")
    assert PRIMARY_KEYWORD in blog_lower
    first_120_words = " ".join(blog_lower.split()[:120])
    assert "signalleaf studio 2.0" in first_120_words
    assert "content operations leads" in first_120_words
    assert "content repurposing workflow" in first_120_words
    for phrase in [
        "signalleaf studio 2.0",
        "april 28, 2026",
        "approval queue",
        "role-based comments",
        "growth",
        "scale",
        "english only",
        "42%",
    ]:
        assert phrase in blog_lower
    assert CTA_URL in blog


def test_linkedin_and_newsletter_follow_channel_constraints():
    _, linkedin, newsletter, _ = _load_outputs()
    linkedin_lower = linkedin.lower()
    assert 90 <= _count_words(linkedin) <= 220
    assert 2 <= _count_hashtags(linkedin) <= 5
    first_line = next(line.strip() for line in linkedin.splitlines() if line.strip())
    assert len(first_line) <= 110
    nonempty_lines = [line.strip() for line in linkedin.splitlines() if line.strip()]
    assert len(nonempty_lines) >= 6
    assert "signalleaf" in linkedin_lower and "studio 2.0" in linkedin_lower
    assert "april 28" in linkedin_lower
    assert "growth" in linkedin_lower and "scale" in linkedin_lower
    assert "english only" in linkedin_lower
    assert CTA_URL in linkedin
    assert ("approval queue" in linkedin_lower) or ("42%" in linkedin_lower)

    assert 38 <= len(newsletter["subject"]) <= 60
    assert 60 <= len(newsletter["preview_text"]) <= 95
    assert 90 <= _count_words(newsletter["body_markdown"]) <= 190
    assert newsletter["cta_url"] == CTA_URL
    assert newsletter["cta_label"].strip()
    body_lower = newsletter["body_markdown"].lower()
    assert "april 28, 2026" in body_lower
    assert "growth" in body_lower and "scale" in body_lower
    assert "english only" in body_lower
    assert CTA_URL == newsletter["cta_url"]
    assert "content operations leads" in body_lower
    assert ("review" in body_lower) or ("handoff" in body_lower)
    assert ("approval queue" in body_lower) or ("42%" in body_lower)


def test_seo_metadata_matches_keyword_plan():
    blog, _, _, seo_meta = _load_outputs()
    assert seo_meta["primary_keyword"] == PRIMARY_KEYWORD
    assert set(seo_meta["secondary_keywords"]) == SECONDARY_KEYWORDS
    assert seo_meta["slug"] in {
        "/blog/content-repurposing-workflow-studio-2-0",
        "content-repurposing-workflow-studio-2-0",
    }
    assert 50 <= len(seo_meta["title"]) <= 65
    assert 145 <= len(seo_meta["description"]) <= 165
    assert PRIMARY_KEYWORD in seo_meta["title"].lower()
    assert "approval queue" in seo_meta["description"].lower()
    seo_desc_lower = seo_meta["description"].lower()
    assert (
        ("growth" in seo_desc_lower and "scale" in seo_desc_lower)
        or ("42%" in seo_desc_lower)
        or ("role-based comments" in seo_desc_lower)
    )
    assert PRIMARY_KEYWORD in blog.lower()
    secondary_hits = sum(keyword in blog.lower() for keyword in SECONDARY_KEYWORDS)
    assert secondary_hits >= 2


def test_cross_channel_consistency_and_differentiation():
    blog, linkedin, newsletter, seo_meta = _load_outputs()
    combined = "\n".join(
        [blog, linkedin, newsletter["subject"], newsletter["preview_text"], newsletter["body_markdown"], seo_meta["title"], seo_meta["description"]]
    ).lower()
    assert not _contains_positive_unsupported_claim(combined)
    for banned_word in ["revolutionary", "game-changing", "10x", "magical"]:
        assert banned_word not in combined

    assert CTA_URL in blog
    assert CTA_URL in linkedin
    assert newsletter["cta_url"] == CTA_URL

    assert _jaccard(blog, linkedin) < 0.55
    assert _jaccard(blog, newsletter["body_markdown"]) < 0.65
