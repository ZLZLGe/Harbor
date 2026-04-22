#!/usr/bin/env python3
import json
import re
from pathlib import Path


ROOT = Path("/root")


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9%+-]+", text))


def count_hashtags(text: str) -> int:
    return len(re.findall(r"(^|\s)#\w+", text))


def read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    blog = read_optional_text(ROOT / "blog_post.md")
    linkedin = read_optional_text(ROOT / "linkedin_post.md")
    newsletter = read_optional_json(ROOT / "newsletter.json")
    seo_meta = read_optional_json(ROOT / "seo_meta.json")

    print(f"blog_exists: {bool(blog)}")
    print(f"blog_word_count: {count_words(blog)}")
    print(f"blog_h2_sections: {blog.count(chr(10) + '## ')}")
    print(f"linkedin_exists: {bool(linkedin)}")
    print(f"linkedin_word_count: {count_words(linkedin)}")
    print(f"linkedin_hashtags: {count_hashtags(linkedin)}")
    nonempty_lines = [line.strip() for line in linkedin.splitlines() if line.strip()]
    if nonempty_lines:
        print(f"linkedin_first_line_length: {len(nonempty_lines[0])}")
    if newsletter:
        print(f"newsletter_subject_length: {len(newsletter.get('subject', ''))}")
        print(f"newsletter_preview_length: {len(newsletter.get('preview_text', ''))}")
        print(f"newsletter_body_word_count: {count_words(newsletter.get('body_markdown', ''))}")
        print(f"newsletter_cta_url: {newsletter.get('cta_url', '')}")
        print("newsletter_subject_target_range: 38-60")
        print("newsletter_preview_target_range: 60-95")
        print("newsletter_body_word_target_range: 90-190")
    if seo_meta:
        print(f"seo_title_length: {len(seo_meta.get('title', ''))}")
        print(f"seo_description_length: {len(seo_meta.get('description', ''))}")
        print(f"seo_primary_keyword: {seo_meta.get('primary_keyword', '')}")
        print(f"seo_slug: {seo_meta.get('slug', '')}")
        print("seo_title_target_range: 50-65")
        print("seo_description_target_range: 145-165")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
