#!/usr/bin/env python3
import json
import re
from pathlib import Path


ROOT = Path("/root")
CTA_URL = "https://signalleaf.example.com/studio-waitlist"
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
NEGATION_HINTS = [
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


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9%+-]+", text))


def hashtags(text: str) -> int:
    return len(re.findall(r"(^|\s)#\w+", text))


def load_optional_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_optional_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def contains_positive_unsupported_claim(text: str) -> bool:
    sentences = [segment.strip().lower() for segment in re.split(r"(?<=[.!?])\s+|\n+", text) if segment.strip()]
    for sentence in sentences:
        for phrase in FORBIDDEN_PHRASES:
            if phrase in sentence:
                if any(negation in sentence for negation in NEGATION_HINTS):
                    continue
                return True
    return False


def check_blog(text: str) -> list[str]:
    issues = []
    low = text.lower()
    if "# " not in text:
        issues.append("missing markdown H1 title")
    if "content repurposing workflow" not in low:
        issues.append("missing primary keyword")
    if "signalleaf studio 2.0" not in low:
        issues.append("missing product name")
    if count_words(text) < 380:
        issues.append("too short for a publish-ready blog post")
    if text.count("\n## ") < 3:
        issues.append("needs at least three H2 sections")
    for phrase in ["approval queue", "growth", "scale", "english only", "42%", "april 28, 2026"]:
        if phrase not in low:
            issues.append(f"missing fact: {phrase}")
    if CTA_URL not in text:
        issues.append("missing official CTA URL")
    return issues


def check_linkedin(text: str) -> list[str]:
    issues = []
    low = text.lower()
    nonempty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if nonempty_lines and len(nonempty_lines[0]) > 110:
        issues.append("first LinkedIn line should stay roughly under 110 characters")
    if count_words(text) < 90:
        issues.append("too short for LinkedIn")
    if hashtags(text) < 2 or hashtags(text) > 5:
        issues.append("hashtag count should stay between 2 and 5")
    if "signalleaf studio 2.0" not in low:
        issues.append("missing product name")
    if CTA_URL not in text:
        issues.append("missing official CTA URL")
    fact_hits = 0
    for ok in [
        "approval queue" in low,
        "42%" in low,
        ("growth" in low and "scale" in low),
        "english only" in low,
        "april 28, 2026" in low,
    ]:
        if ok:
            fact_hits += 1
    if fact_hits < 3:
        issues.append("needs at least three core facts")
    return issues


def check_newsletter(payload: dict) -> list[str]:
    issues = []
    if not payload:
        return ["newsletter.json missing"]
    body = payload.get("body_markdown", "")
    subject_length = len(payload.get("subject", ""))
    preview_length = len(payload.get("preview_text", ""))
    body_word_count = count_words(body)
    if subject_length < 38 or subject_length > 60:
        issues.append(f"subject length out of range: {subject_length} (target 38-60)")
    if preview_length < 60 or preview_length > 95:
        issues.append(f"preview text length out of range: {preview_length} (target 60-95)")
    if body_word_count < 90 or body_word_count > 190:
        issues.append(f"newsletter body word count out of range: {body_word_count} (target 90-190)")
    if payload.get("cta_url") != CTA_URL:
        issues.append("newsletter CTA URL mismatch")
    body_low = body.lower()
    if "april 28, 2026" not in body_low:
        issues.append("newsletter must include the exact date string April 28, 2026")
    if not ("growth" in body_low and "scale" in body_low):
        issues.append("newsletter must mention Growth and Scale")
    if "english only" not in body_low:
        issues.append("newsletter must mention English only")
    if not (("approval queue" in body_low) or ("42%" in body_low)):
        issues.append("newsletter must mention approval queue or the 42% beta result")
    return issues


def check_seo(payload: dict) -> list[str]:
    issues = []
    if not payload:
        return ["seo_meta.json missing"]
    if payload.get("primary_keyword") != "content repurposing workflow":
        issues.append("primary keyword mismatch")
    if payload.get("slug") != "/blog/content-repurposing-workflow-studio-2-0":
        issues.append("slug mismatch")
    title_length = len(payload.get("title", ""))
    description_raw = payload.get("description", "")
    description_length = len(description_raw)
    description = description_raw.lower()
    if title_length < 50 or title_length > 65:
        issues.append(f"seo title length out of range: {title_length} (target 50-65)")
    if description_length < 145 or description_length > 165:
        issues.append(f"seo description length out of range: {description_length} (target 145-165)")
    if "approval queue" not in description:
        issues.append("seo description must mention approval queue")
    if not (
        ("growth" in description and "scale" in description)
        or ("42%" in description)
        or ("role-based comments" in description)
    ):
        issues.append("seo description must mention Growth and Scale, the 42% beta result, or role-based comments")
    return issues


def main() -> int:
    blog = load_optional_text(ROOT / "blog_post.md")
    linkedin = load_optional_text(ROOT / "linkedin_post.md")
    newsletter = load_optional_json(ROOT / "newsletter.json")
    seo_meta = load_optional_json(ROOT / "seo_meta.json")

    checks = {
        "blog_post": check_blog(blog),
        "linkedin_post": check_linkedin(linkedin),
        "newsletter": check_newsletter(newsletter),
        "seo_meta": check_seo(seo_meta),
    }
    combined = "\n".join(
        [
            blog,
            linkedin,
            newsletter.get("subject", ""),
            newsletter.get("preview_text", ""),
            newsletter.get("body_markdown", ""),
            seo_meta.get("title", ""),
            seo_meta.get("description", ""),
        ]
    )

    has_issues = False
    for name, issues in checks.items():
        print(f"[{name}]")
        if not issues:
            print("  OK")
            continue
        has_issues = True
        for issue in issues:
            print(f"  - {issue}")
    if contains_positive_unsupported_claim(combined):
        has_issues = True
        print("[bundle_claims]")
        print("  - positive unsupported claim detected in final bundle")
    if has_issues:
        return 1
    print("\nALL_CHECKS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
