#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


ROOT = Path(os.environ.get("CONTENT_ROOT", "/root"))
OUTPUT_PATH = Path(os.environ.get("PUBLISH_BUNDLE_OUTPUT_PATH", "/root/publish_bundle.json"))


def _read_required_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def _read_required_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _word_count(text: str) -> int:
    return len(text.split())


def main() -> int:
    try:
        blog_post = _read_required_text(ROOT / "blog_post.md")
        linkedin_post = _read_required_text(ROOT / "linkedin_post.md")
        newsletter = _read_required_json(ROOT / "newsletter.json")
        seo_meta = _read_required_json(ROOT / "seo_meta.json")
        fact_sheet = _read_required_json(ROOT / "fact_sheet.json")
        keyword_plan = _read_required_json(ROOT / "keyword_plan.json")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Failed to package launch bundle: {exc}", file=sys.stderr)
        return 2

    payload = {
        "bundle_id": "signalleaf-studio-2-0-launch",
        "product_name": fact_sheet["product_name"],
        "launch_date": fact_sheet["launch_date"],
        "primary_keyword": keyword_plan["primary_keyword"],
        "artifacts": {
            "blog_post_path": "/root/blog_post.md",
            "linkedin_post_path": "/root/linkedin_post.md",
            "newsletter_path": "/root/newsletter.json",
            "seo_meta_path": "/root/seo_meta.json",
        },
        "stats": {
            "blog_word_count": _word_count(blog_post),
            "linkedin_word_count": _word_count(linkedin_post),
            "newsletter_body_word_count": _word_count(newsletter["body_markdown"]),
            "newsletter_subject_length": len(newsletter["subject"]),
            "newsletter_preview_length": len(newsletter["preview_text"]),
            "seo_title_length": len(seo_meta["title"]),
            "seo_description_length": len(seo_meta["description"]),
        },
        "cta_url": newsletter["cta_url"],
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
