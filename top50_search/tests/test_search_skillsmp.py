import json
import unittest

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from top50_search.src.search_skillsmp import (
    normalize_search_skill,
    dedupe_candidates,
    search_bucket_candidates,
    SearchSkillsMPError,
)


class DummyScraper:
    def __init__(self, fixtures: dict[str, Any]):
        self.fixtures = fixtures

        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, timeout: int, headers: dict[str, str] | None = None):
        query = self._extract_query(url)
        if not query:
            raise RuntimeError("missing query")
        if "schema" in query:
            fixture = self.fixtures["schema_validation"]
        elif "data" in query:
            fixture = self.fixtures["data_quality"]
        else:
            raise RuntimeError(f"no fixture for {query}")
        self.calls.append({"url": url, "headers": headers or {}})
        return DummyResponse(fixture)

    @staticmethod
    def _extract_query(url: str) -> str | None:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        for key in ("search", "query", "q"):
            values = params.get(key)
            if values:
                return values[0].lower()
        return None


class DummyResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class SearchSkillsMPSmokeTest(unittest.TestCase):
    def setUp(self):
        fixture_dir = Path(__file__).resolve().parent / "fixtures" / "search_skillsmp"
        self.fixtures = {
            "data_quality": json.loads((fixture_dir / "search_page_data_quality.json").read_text(encoding="utf-8")),
            "schema_validation": json.loads((fixture_dir / "search_page_schema_validation.json").read_text(encoding="utf-8")),
        }
        self.scraper = DummyScraper(self.fixtures)

    def test_normalize_shape(self):
        raw = self.fixtures["data_quality"]["results"][0]
        candidate = normalize_search_skill(raw, query="data quality")
        expected_fields = {
            "id",
            "name",
            "author",
            "description",
            "github_url",
            "skillsmp_url",
            "stars",
            "forks",
            "queries",
        }
        self.assertEqual(set(candidate), expected_fields)
        self.assertEqual(candidate["queries"], ["data quality"])

    def test_dedupe_same_skill(self):
        candidates = [
            normalize_search_skill(self.fixtures["data_quality"]["results"][1], query="data quality"),
            normalize_search_skill(self.fixtures["schema_validation"]["skills"][1], query="schema validation"),
        ]
        deduped = dedupe_candidates(candidates)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["queries"], ["data quality", "schema validation"])

    def test_search_bucket_aggregates_seed_and_expand(self):
        bucket = {
            "seed_queries": ["data quality"],
            "expand_queries": ["schema validation"],
            "candidate_limit": 2,
            "target_limit": 2,
        }
        results = search_bucket_candidates(self.scraper, bucket)
        self.assertEqual(len(results), 2)
        queries = {q for candidate in results for q in candidate.get("queries", [])}
        self.assertIn("data quality", queries)
        self.assertIn("schema validation", queries)

    def test_official_q_param_used(self):
        bucket = {"seed_queries": ["data quality"], "candidate_limit": 1, "target_limit": 1}
        search_bucket_candidates(self.scraper, bucket)
        self.assertTrue(self.scraper.calls)
        first_call = self.scraper.calls[0]
        params = parse_qs(urlparse(first_call["url"]).query)
        self.assertEqual(params.get("q"), ["data quality"])

    def test_bearer_header_propagates(self):
        bucket = {
            "seed_queries": ["data quality"],
            "candidate_limit": 1,
            "target_limit": 1,
            "auth_token": "secret",
        }
        search_bucket_candidates(self.scraper, bucket)
        self.assertTrue(self.scraper.calls)
        headers = self.scraper.calls[0]["headers"]
        self.assertEqual(headers.get("Authorization"), "Bearer secret")

    def test_search_bucket_accepts_nested_data_skills_payload(self):
        nested_payload = {
            "success": True,
            "data": {
                "skills": [
                    {
                        "id": "live-01",
                        "name": "data-quality-frameworks",
                        "author": "live-author",
                        "description": "Implement data quality validation with explicit checks.",
                        "githubUrl": "https://github.com/example/repo/tree/main/skills/data-quality-frameworks",
                        "skillUrl": "https://skillsmp.com/skills/live-01",
                        "stars": 42,
                    }
                ]
            },
        }
        scraper = DummyScraper({"data_quality": nested_payload, "schema_validation": self.fixtures["schema_validation"]})
        bucket = {"seed_queries": ["data quality"], "candidate_limit": 5, "target_limit": 5}

        results = search_bucket_candidates(scraper, bucket)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "live-01")
        self.assertEqual(results[0]["skillsmp_url"], "https://skillsmp.com/skills/live-01")

    def test_search_bucket_raises_when_fetch_fails(self):
        bucket = {"seed_queries": ["missing"], "target_limit": 1, "candidate_limit": 1}
        with self.assertRaises(SearchSkillsMPError):
            search_bucket_candidates(self.scraper, bucket)
