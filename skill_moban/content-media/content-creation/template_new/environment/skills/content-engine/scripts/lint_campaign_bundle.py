from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


OUTPUT_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/root/output")
SOURCE_ROOT = Path(os.environ.get("SOURCE_BUNDLE_ROOT", "/root/workspace/source_bundle"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text.lower())


def word_count(text: str) -> int:
    return len(words(text))


def paragraph_count(text: str) -> int:
    count = 0
    in_paragraph = False
    for line in text.splitlines():
        if line.strip():
            if not in_paragraph:
                count += 1
                in_paragraph = True
        else:
            in_paragraph = False
    return count


def h2_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("## "))


def thread_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if re.match(r"^\d+/", line.strip())]


def parse_ref(ref: str) -> tuple[Path, int, int]:
    path_part, line_part = ref.split("#", 1)
    start_text, end_text = line_part[1:].split("-L")
    start = int(start_text)
    end = int(end_text)
    return SOURCE_ROOT / path_part, start, end


def main() -> None:
    constraints = load_json(SOURCE_ROOT / "campaign_constraints.json")
    red_flags = {
        line.strip().lower()
        for line in (SOURCE_ROOT / "style_red_flags.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    source_map = load_json(OUTPUT_ROOT / "source_map.json")
    issues: list[str] = []

    if source_map.get("anchor_asset") != "anchor_article.md":
        issues.append("anchor_asset must be anchor_article.md")

    required_limits = constraints.get("required_shared_limits", [])
    actual_limits = source_map.get("shared_limits", [])
    if actual_limits != required_limits:
        issues.append("source_map shared_limits must match required_shared_limits exactly")

    campaign_lines = [
        line.rstrip()
        for line in (OUTPUT_ROOT / "campaign_summary.md").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if (OUTPUT_ROOT / "campaign_summary.md").exists() else []
    if len(campaign_lines) < 4:
        issues.append("campaign_summary.md must include one summary line and three channel bullets")
    elif campaign_lines[0].startswith("- "):
        issues.append("campaign_summary.md first line must be a summary sentence")
    else:
        bullet_lines = [line for line in campaign_lines[1:] if line.startswith("- ")]
        if len(bullet_lines) != 3:
            issues.append("campaign_summary.md must contain exactly three channel bullets")
        lowered_bullets = "\n".join(bullet_lines).lower()
        for channel in ["x", "linkedin", "newsletter"]:
            if channel not in lowered_bullets:
                issues.append(f"campaign_summary.md must mention {channel}")

    entries = {item["file"]: item for item in source_map.get("deliverables", [])}
    for spec in constraints["deliverables"]:
        file_name = spec["file"]
        path = OUTPUT_ROOT / file_name
        if not path.exists():
            issues.append(f"missing output file: {file_name}")
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in red_flags:
            if phrase in lowered:
                issues.append(f"{file_name} contains red flag phrase: {phrase}")
        entry = entries.get(file_name)
        if not entry:
            issues.append(f"source_map missing entry for {file_name}")
            continue
        refs = entry.get("source_refs", [])
        if len(refs) < spec["min_source_refs"]:
            issues.append(f"{file_name} has too few source refs")
        distinct_files = {ref.split("#", 1)[0] for ref in refs}
        if len(distinct_files) < spec["min_distinct_files"]:
            issues.append(f"{file_name} cites too few distinct files")
        for ref in refs:
            try:
                file_path, start, end = parse_ref(ref)
            except Exception:
                issues.append(f"{file_name} has invalid ref syntax: {ref}")
                continue
            if not file_path.exists():
                issues.append(f"{file_name} cites missing source file: {ref}")
                continue
            line_count = len(file_path.read_text(encoding="utf-8").splitlines())
            if start < 1 or end < start or end > line_count:
                issues.append(f"{file_name} cites out-of-range lines: {ref}")
        hits = sum(1 for keyword in spec["required_keywords"] if keyword.lower() in lowered)
        if hits < 3:
            issues.append(f"{file_name} does not reflect enough channel keywords")

        if file_name == "x_thread.md":
            numbered_lines = thread_lines(text)
            if not 5 <= len(numbered_lines) <= 7:
                issues.append("x_thread.md must contain 5 to 7 numbered lines")
            for idx, line in enumerate(numbered_lines, start=1):
                if not line.startswith(f"{idx}/"):
                    issues.append(f"x_thread.md numbering gap at line {idx}")
                    break
        elif file_name == "linkedin_post.md":
            min_words, max_words = spec["word_range"]
            total_words = word_count(text)
            if total_words < min_words or total_words > max_words:
                issues.append("linkedin_post.md word count is out of range")
            if paragraph_count(text) > 6:
                issues.append("linkedin_post.md has too many paragraphs")
        elif file_name == "newsletter_draft.md":
            lines = text.splitlines()
            if len(lines) < 2 or not lines[0].startswith("Subject:"):
                issues.append("newsletter_draft.md must start with Subject:")
            if len(lines) < 2 or not lines[1].startswith("Preview:"):
                issues.append("newsletter_draft.md second line must start with Preview:")
            min_words, max_words = spec["word_range"]
            total_words = word_count(text)
            if total_words < min_words or total_words > max_words:
                issues.append("newsletter_draft.md word count is out of range")
            if h2_count(text) < 3:
                issues.append("newsletter_draft.md must contain at least three H2 sections")

    texts = {}
    for file_name in ["x_thread.md", "linkedin_post.md", "newsletter_draft.md"]:
        path = OUTPUT_ROOT / file_name
        if path.exists():
            texts[file_name] = set(words(path.read_text(encoding="utf-8")))
    keys = sorted(texts)
    for idx, left in enumerate(keys):
        for right in keys[idx + 1:]:
            overlap = texts[left] & texts[right]
            union = texts[left] | texts[right]
            if union and len(overlap) / len(union) > 0.55:
                issues.append(f"{left} and {right} overlap too much")

    if issues:
        print(json.dumps({"ok": False, "issues": issues}, indent=2))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "issues": []}, indent=2))


if __name__ == "__main__":
    main()
