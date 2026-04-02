from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.skillsmp_snapshot import (
    API_PAGE_LIMIT,
    SkillsMPSnapshotError,
    Subcategory,
    build_skills_api_url,
    build_snapshot_document,
    fetch_subcategory_snapshot,
    parse_category_tree,
    sort_and_limit_skills,
    write_subcategory_snapshot_files,
    write_yaml,
)


FIXTURES = Path(__file__).parent / "fixtures"


class ParseCategoryTreeTest(unittest.TestCase):
    def test_parses_major_categories_and_subcategories(self) -> None:
        html = (FIXTURES / "categories_sample.html").read_text(encoding="utf-8")

        result = parse_category_tree(html)

        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].category_slug, "development")
        self.assertEqual(result[0].subcategory_slug, "frontend")
        self.assertEqual(result[0].subcategory_skill_count, 17262)
        self.assertEqual(result[2].category_slug, "devops")
        self.assertEqual(result[2].subcategory_name, "CI/CD")


class BuildSkillsApiUrlTest(unittest.TestCase):
    def test_uses_category_param_and_stars_sort(self) -> None:
        url = build_skills_api_url("frontend", limit=50, page=2)

        self.assertEqual(
            url,
            "https://skillsmp.com/api/skills?page=2&limit=50&sortBy=stars&category=frontend",
        )


class SortAndLimitSkillsTest(unittest.TestCase):
    def test_applies_local_tie_breakers_and_ranking(self) -> None:
        raw_skills = [
            {"id": "b", "name": "beta", "author": "x", "stars": 10, "forks": 1},
            {"id": "a", "name": "alpha", "author": "x", "stars": 10, "forks": 1},
            {"id": "c", "name": "charlie", "author": "x", "stars": 12, "forks": 0},
            {"id": "d", "name": "delta", "author": "x", "stars": 10, "forks": 5},
        ]

        result = sort_and_limit_skills(raw_skills, limit=3)

        self.assertEqual([item["id"] for item in result], ["c", "d", "a"])
        self.assertEqual([item["rank"] for item in result], [1, 2, 3])


class FetchSubcategorySnapshotTest(unittest.TestCase):
    def test_fetches_multiple_pages_when_requested_limit_exceeds_page_cap(self) -> None:
        subcategory = Subcategory(
            category_slug="development",
            category_name="Development",
            category_skill_count=999,
            subcategory_slug="frontend",
            subcategory_name="Frontend",
            subcategory_skill_count=999,
        )
        calls: list[str] = []

        def fake_fetch_json(_scraper: object, url: str) -> dict[str, object]:
            calls.append(url)
            if "page=1" in url:
                skills = [
                    {"id": f"skill-{index:03d}", "name": f"Skill {index:03d}", "author": "x", "stars": 1000 - index, "forks": 0}
                    for index in range(1, API_PAGE_LIMIT + 1)
                ]
                return {
                    "skills": skills,
                    "pagination": {"page": 1, "limit": API_PAGE_LIMIT, "hasNext": True, "hasPrev": False, "totalPages": 2},
                }
            skills = [
                {"id": f"skill-{index:03d}", "name": f"Skill {index:03d}", "author": "x", "stars": 1000 - index, "forks": 0}
                for index in range(API_PAGE_LIMIT + 1, 201)
            ]
            return {
                "skills": skills,
                "pagination": {"page": 2, "limit": API_PAGE_LIMIT, "hasNext": False, "hasPrev": True, "totalPages": 2},
            }

        snapshot = fetch_subcategory_snapshot(
            object(),
            subcategory,
            limit=200,
            fetch_json_fn=fake_fetch_json,
        )

        self.assertEqual(
            calls,
            [
                "https://skillsmp.com/api/skills?page=1&limit=100&sortBy=stars&category=frontend",
                "https://skillsmp.com/api/skills?page=2&limit=100&sortBy=stars&category=frontend",
            ],
        )
        self.assertEqual(snapshot["requested_limit"], 200)
        self.assertEqual(snapshot["fetched_count"], 200)
        self.assertEqual(len(snapshot["skills"]), 200)
        self.assertEqual(snapshot["source_url"], calls[0])
        self.assertEqual(snapshot["source_urls"], calls)
        self.assertEqual(snapshot["pagination"]["pages_fetched"], 2)
        self.assertEqual(snapshot["skills"][0]["id"], "skill-001")
        self.assertEqual(snapshot["skills"][-1]["id"], "skill-200")

    def test_dedupes_across_pages_and_continues_until_limit_is_satisfied(self) -> None:
        subcategory = Subcategory(
            category_slug="development",
            category_name="Development",
            category_skill_count=999,
            subcategory_slug="frontend",
            subcategory_name="Frontend",
            subcategory_skill_count=999,
        )
        calls: list[str] = []

        def fake_fetch_json(_scraper: object, url: str) -> dict[str, object]:
            calls.append(url)
            if "page=1" in url:
                skills = [
                    {"id": f"skill-{index:03d}", "name": f"Skill {index:03d}", "author": "x", "stars": 500 - index, "forks": 0}
                    for index in range(1, API_PAGE_LIMIT + 1)
                ]
                return {
                    "skills": skills,
                    "pagination": {"page": 1, "limit": API_PAGE_LIMIT, "hasNext": True, "hasPrev": False},
                }
            if "page=2" in url:
                skills = [
                    {"id": "skill-100", "name": "Skill 100", "author": "x", "stars": 400, "forks": 0},
                    {"id": "skill-101", "name": "Skill 101", "author": "x", "stars": 399, "forks": 0},
                ]
                return {
                    "skills": skills,
                    "pagination": {"page": 2, "limit": API_PAGE_LIMIT, "hasNext": True, "hasPrev": True},
                }
            return {
                "skills": [
                    {"id": "skill-102", "name": "Skill 102", "author": "x", "stars": 398, "forks": 0},
                ],
                "pagination": {"page": 3, "limit": API_PAGE_LIMIT, "hasNext": False, "hasPrev": True},
            }

        snapshot = fetch_subcategory_snapshot(
            object(),
            subcategory,
            limit=102,
            fetch_json_fn=fake_fetch_json,
        )

        self.assertEqual(len(calls), 3)
        self.assertEqual(snapshot["fetched_count"], 102)
        self.assertEqual([item["id"] for item in snapshot["skills"][-2:]], ["skill-101", "skill-102"])
        self.assertEqual(snapshot["pagination"]["pages_fetched"], 3)

    def test_raises_when_limit_is_not_positive(self) -> None:
        subcategory = Subcategory(
            category_slug="development",
            category_name="Development",
            category_skill_count=1,
            subcategory_slug="frontend",
            subcategory_name="Frontend",
            subcategory_skill_count=1,
        )

        with self.assertRaises(SkillsMPSnapshotError):
            fetch_subcategory_snapshot(object(), subcategory, limit=0, fetch_json_fn=lambda *_args, **_kwargs: {})


class WriteYamlTest(unittest.TestCase):
    def test_writes_expected_top_level_keys(self) -> None:
        subcategories = [
            Subcategory(
                category_slug="development",
                category_name="Development",
                category_skill_count=100,
                subcategory_slug="frontend",
                subcategory_name="Frontend",
                subcategory_skill_count=50,
            )
        ]
        snapshots = [
            {
                "category_slug": "development",
                "category_name": "Development",
                "subcategory_slug": "frontend",
                "subcategory_name": "Frontend",
                "source_url": "https://skillsmp.com/api/skills?page=1&limit=50&sortBy=stars&category=frontend",
                "source_urls": ["https://skillsmp.com/api/skills?page=1&limit=50&sortBy=stars&category=frontend"],
                "sort": "stars_desc",
                "tie_breaker": "forks_desc_then_name_asc_then_id_asc",
                "requested_limit": 50,
                "fetched_count": 1,
                "pagination": {"page": 1},
                "skills": [{"rank": 1, "id": "alpha", "name": "alpha", "author": "x"}],
            }
        ]

        document = build_snapshot_document(
            subcategories,
            snapshots,
            generated_at="2026-03-30T09:48:22+00:00",
            requested_limit=50,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "snapshot.yaml"
            write_yaml(document, output_path)
            rendered = output_path.read_text(encoding="utf-8")

        self.assertIn("category_tree:", rendered)
        self.assertIn("subcategory_snapshots:", rendered)
        self.assertIn("subcategory_slug: frontend", rendered)
        self.assertIn("requested_limit_per_subcategory: 50", rendered)


class WriteSubcategorySnapshotFilesTest(unittest.TestCase):
    def test_writes_one_yaml_per_subcategory(self) -> None:
        snapshots = [
            {
                "category_slug": "development",
                "category_name": "Development",
                "subcategory_slug": "frontend",
                "subcategory_name": "Frontend",
                "source_url": "https://skillsmp.com/api/skills?page=1&limit=50&sortBy=stars&category=frontend",
                "source_urls": ["https://skillsmp.com/api/skills?page=1&limit=50&sortBy=stars&category=frontend"],
                "sort": "stars_desc",
                "tie_breaker": "forks_desc_then_name_asc_then_id_asc",
                "requested_limit": 50,
                "fetched_count": 1,
                "pagination": {"page": 1},
                "skills": [{"rank": 1, "id": "alpha", "name": "alpha", "author": "x"}],
            },
            {
                "category_slug": "development",
                "category_name": "Development",
                "subcategory_slug": "backend",
                "subcategory_name": "Backend",
                "source_url": "https://skillsmp.com/api/skills?page=1&limit=50&sortBy=stars&category=backend",
                "source_urls": ["https://skillsmp.com/api/skills?page=1&limit=50&sortBy=stars&category=backend"],
                "sort": "stars_desc",
                "tie_breaker": "forks_desc_then_name_asc_then_id_asc",
                "requested_limit": 50,
                "fetched_count": 1,
                "pagination": {"page": 1},
                "skills": [{"rank": 1, "id": "beta", "name": "beta", "author": "x"}],
            },
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "subcategory_top50"
            written_files = write_subcategory_snapshot_files(
                generated_at="2026-03-30T09:48:22+00:00",
                source={
                    "marketplace": "skillsmp",
                    "skills_api_url": "https://skillsmp.com/api/skills",
                },
                snapshots=snapshots,
                output_dir=output_dir,
            )

            self.assertEqual(
                [path.relative_to(output_dir).as_posix() for path in written_files],
                ["development/backend.yaml", "development/frontend.yaml"],
            )
            frontend_rendered = (output_dir / "development" / "frontend.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("subcategory_slug: frontend", frontend_rendered)
            self.assertIn("skills:", frontend_rendered)


if __name__ == "__main__":
    unittest.main()
