from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    import cloudscraper
except ModuleNotFoundError:  # pragma: no cover - exercised through runtime path
    cloudscraper = None


CATEGORIES_URL = "https://skillsmp.com/categories"
SKILLS_API_URL = "https://skillsmp.com/api/skills"
DEFAULT_LIMIT = 50
DEFAULT_TIMEOUT_SECONDS = 30
TIE_BREAKER = "forks_desc_then_name_asc_then_id_asc"


@dataclass(frozen=True)
class Subcategory:
    category_slug: str
    category_name: str
    category_skill_count: int
    subcategory_slug: str
    subcategory_name: str
    subcategory_skill_count: int


class SkillsMPSnapshotError(RuntimeError):
    pass


def parse_count(raw: str) -> int:
    return int(raw.replace(",", ""))


def build_scraper():
    if cloudscraper is None:
        raise SkillsMPSnapshotError(
            "缺少 cloudscraper。请先执行 `python3 -m pip install --target vendor cloudscraper`。"
        )
    return cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "linux", "mobile": False}
    )


def fetch_text(scraper: Any, url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    response = scraper.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_json(scraper: Any, url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    response = scraper.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def parse_category_tree(categories_html: str) -> list[Subcategory]:
    heading_re = re.compile(
        r'<h2 class="text-xl font-bold text-foreground"><span class="text-[^"]+">'
        r"export<!-- --> </span>(?P<name>[^<]+)</h2>"
        r"\s*"
        r'<p class="text-xs text-muted-foreground"><span class="text-green-600 dark:text-green-400">'
        r"// </span>(?P<count>[0-9,]+)<!-- --> <!-- -->skills</p>"
    )
    card_re = re.compile(
        r'href="/categories/(?P<slug>[^"]+)"><div class="px-4 py-2 bg-muted/30 border-b border-border '
        r'flex items-center justify-between"><span class="font-mono text-xs text-muted-foreground">'
        r"(?P<file_slug>[^<]+)<!-- -->\.ts</span>.*?"
        r'<span class="font-semibold [^"]+">(?P<name>[^<]+)</span>.*?'
        r'<span class="text-primary font-medium">(?P<count>[0-9,]+)</span> <!-- -->skills'
    )

    headings = list(heading_re.finditer(categories_html))
    if not headings:
        raise SkillsMPSnapshotError("未能从分类页解析出任何大类。页面结构可能已变化。")

    subcategories: list[Subcategory] = []
    for index, heading in enumerate(headings):
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(categories_html)
        section = categories_html[start:end]
        category_name = html.unescape(heading.group("name"))
        category_slug = slugify(category_name)
        category_skill_count = parse_count(heading.group("count"))

        seen_slugs: set[str] = set()
        for match in card_re.finditer(section):
            sub_slug = match.group("slug")
            if sub_slug in seen_slugs:
                continue
            seen_slugs.add(sub_slug)
            subcategories.append(
                Subcategory(
                    category_slug=category_slug,
                    category_name=category_name,
                    category_skill_count=category_skill_count,
                    subcategory_slug=sub_slug,
                    subcategory_name=html.unescape(match.group("name")),
                    subcategory_skill_count=parse_count(match.group("count")),
                )
            )

    if not subcategories:
        raise SkillsMPSnapshotError("未能从分类页解析出任何小类。页面结构可能已变化。")
    return subcategories


def slugify(name: str) -> str:
    value = html.unescape(name).lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def build_skills_api_url(subcategory_slug: str, limit: int = DEFAULT_LIMIT, page: int = 1) -> str:
    return (
        f"{SKILLS_API_URL}?page={page}&limit={limit}&sortBy=stars&category={subcategory_slug}"
    )


def normalize_skill(raw: dict[str, Any], rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "id": raw["id"],
        "name": raw["name"],
        "author": raw["author"],
        "stars": int(raw.get("stars") or 0),
        "forks": int(raw.get("forks") or 0),
        "description": raw.get("description") or "",
        "github_url": raw.get("githubUrl") or "",
        "updated_at": raw.get("updatedAt") or "",
    }


def sort_and_limit_skills(raw_skills: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ordered = sorted(
        raw_skills,
        key=lambda item: (
            -int(item.get("stars") or 0),
            -int(item.get("forks") or 0),
            str(item.get("name") or "").lower(),
            str(item.get("id") or "").lower(),
        ),
    )
    limited = ordered[:limit]
    return [normalize_skill(skill, rank=index) for index, skill in enumerate(limited, start=1)]


def fetch_subcategory_snapshot(
    scraper: Any, subcategory: Subcategory, limit: int = DEFAULT_LIMIT
) -> dict[str, Any]:
    url = build_skills_api_url(subcategory.subcategory_slug, limit=limit, page=1)
    payload = fetch_json(scraper, url)
    skills = sort_and_limit_skills(payload.get("skills", []), limit=limit)
    pagination = payload.get("pagination", {})
    return {
        "category_slug": subcategory.category_slug,
        "category_name": subcategory.category_name,
        "category_skill_count": subcategory.category_skill_count,
        "subcategory_slug": subcategory.subcategory_slug,
        "subcategory_name": subcategory.subcategory_name,
        "subcategory_skill_count": subcategory.subcategory_skill_count,
        "source_url": url,
        "sort": "stars_desc",
        "tie_breaker": TIE_BREAKER,
        "requested_limit": limit,
        "fetched_count": len(skills),
        "pagination": {
            "page": pagination.get("page"),
            "limit": pagination.get("limit"),
            "total": pagination.get("total"),
            "total_pages": pagination.get("totalPages"),
            "has_next": pagination.get("hasNext"),
            "has_prev": pagination.get("hasPrev"),
            "total_all": pagination.get("totalAll"),
            "is_capped": pagination.get("isCapped"),
            "max_results": pagination.get("maxResults"),
        },
        "skills": skills,
    }


def build_snapshot_document(
    subcategories: list[Subcategory],
    snapshots: list[dict[str, Any]],
    *,
    generated_at: str,
    requested_limit: int,
) -> dict[str, Any]:
    return {
        "generated_at": generated_at,
        "source": {
            "marketplace": "skillsmp",
            "categories_url": CATEGORIES_URL,
            "skills_api_url": SKILLS_API_URL,
            "sort": "stars_desc",
            "tie_breaker": TIE_BREAKER,
            "requested_limit_per_subcategory": requested_limit,
        },
        "category_tree": [
            {
                "category_slug": category_slug,
                "category_name": rows[0].category_name,
                "category_skill_count": rows[0].category_skill_count,
                "subcategories": [
                    {
                        "subcategory_slug": row.subcategory_slug,
                        "subcategory_name": row.subcategory_name,
                        "subcategory_skill_count": row.subcategory_skill_count,
                    }
                    for row in rows
                ],
            }
            for category_slug, rows in group_subcategories(subcategories).items()
        ],
        "subcategory_snapshots": snapshots,
    }


def group_subcategories(subcategories: list[Subcategory]) -> dict[str, list[Subcategory]]:
    grouped: dict[str, list[Subcategory]] = {}
    for item in subcategories:
        grouped.setdefault(item.category_slug, []).append(item)
    return grouped


def write_yaml(document: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def build_subcategory_snapshot_document(
    *,
    generated_at: str,
    source: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generated_at": generated_at,
        "source": source,
        **snapshot,
    }


def write_subcategory_snapshot_files(
    *,
    generated_at: str,
    source: dict[str, Any],
    snapshots: list[dict[str, Any]],
    output_dir: Path,
) -> list[Path]:
    written_files: list[Path] = []
    for snapshot in sorted(
        snapshots,
        key=lambda item: (
            item["category_slug"],
            item["subcategory_slug"],
        ),
    ):
        output_path = output_dir / snapshot["category_slug"] / f'{snapshot["subcategory_slug"]}.yaml'
        document = build_subcategory_snapshot_document(
            generated_at=generated_at,
            source=source,
            snapshot=snapshot,
        )
        write_yaml(document, output_path)
        written_files.append(output_path)
    return written_files


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate skillsmp subcategory hot skills snapshot.")
    parser.add_argument(
        "--output",
        default="subcategory_hot_skills_snapshot.yaml",
        help="Output YAML path.",
    )
    parser.add_argument(
        "--per-subcategory-dir",
        default="subcategory_top50",
        help="Directory for one YAML file per subcategory.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Top N skills per subcategory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    scraper = build_scraper()
    categories_html = fetch_text(scraper, CATEGORIES_URL)
    subcategories = parse_category_tree(categories_html)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshots = [
        fetch_subcategory_snapshot(scraper, subcategory, limit=args.limit)
        for subcategory in subcategories
    ]
    document = build_snapshot_document(
        subcategories,
        snapshots,
        generated_at=generated_at,
        requested_limit=args.limit,
    )
    source = document["source"]
    write_yaml(document, Path(args.output))
    written_files = write_subcategory_snapshot_files(
        generated_at=generated_at,
        source=source,
        snapshots=snapshots,
        output_dir=Path(args.per_subcategory_dir),
    )
    print(
        json.dumps(
            {
                "output": str(Path(args.output).resolve()),
                "per_subcategory_dir": str(Path(args.per_subcategory_dir).resolve()),
                "categories": len(group_subcategories(subcategories)),
                "subcategories": len(subcategories),
                "subcategory_files": len(written_files),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
