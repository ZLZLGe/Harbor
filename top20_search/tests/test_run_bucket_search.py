import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from top20_search.src import run_bucket_search

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs/domains_and_buckets.yaml"
FIT_RULES_PATH = Path(__file__).resolve().parents[1] / "configs/harbor_fit_rules.yaml"

KEY_SEED_QUERIES = {"data quality auditor", "schema validation", "data profiling"}

KEY_EXPAND_QUERIES = {"deduplication", "csv validation", "open data quality"}

KEY_EXCLUDE_TERMS = {"install skill", "registry", "framework", "reference"}


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def load_harbor_fit_rules():
    with open(FIT_RULES_PATH, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def sample_selected_entries(fixtures_root: Path):
    return [
        {
            "rank": 1,
            "id": "data-quality-audit",
            "name": "Data Quality Audit",
            "author": "QA Team",
            "skillsmp_url": "https://skillsmp.com/skills/data-quality-audit",
            "github_url": "https://github.com/example/data-quality-audit",
            "bundle_path": fixtures_root / "data-quality-audit",
        },
        {
            "rank": 2,
            "id": "meta-registry-skill",
            "name": "Meta Registry Sketch",
            "author": "Registry Guild",
            "skillsmp_url": "https://skillsmp.com/skills/meta-registry-skill",
            "github_url": "https://github.com/example/meta-registry-skill",
            "bundle_path": fixtures_root / "meta-registry-skill",
        },
    ]


class Top20SearchConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def test_data_quality_bucket_configuration(self):
        self.assertIsInstance(self.config, dict, "Expected top-level mapping in domains_and_buckets.yaml")

        domains = self.config.get("domains")
        self.assertIsInstance(domains, list, "domains must be a list")
        domain_slugs = {domain.get("slug") for domain in domains if isinstance(domain, dict)}
        self.assertIn("data-ml-engineering", domain_slugs)

        buckets = self.config.get("search_buckets")
        self.assertIsInstance(buckets, list, "search_buckets must be a list")
        bucket_slugs = {item.get("slug") for item in buckets if isinstance(item, dict)}
        self.assertTrue(
            {"data-quality", "xlsx", "portfolio-management", "debugging", "bioinformatics"}.issubset(bucket_slugs)
        )
        bucket = next((item for item in buckets if isinstance(item, dict) and item.get("slug") == "data-quality"), None)
        self.assertIsNotNone(bucket, "data-quality bucket must be present in search_buckets")

        self.assertEqual(bucket.get("domain"), "data-ml-engineering")
        self.assertEqual(bucket.get("selected_target"), 20)
        self.assertEqual(bucket.get("candidate_limit"), 100)

        seed_queries = bucket.get("seed_queries")
        self.assertIsInstance(seed_queries, list, "seed_queries must be a list")
        self.assertTrue(all(isinstance(item, str) for item in seed_queries), "seed_queries entries must be strings")
        self.assertTrue(KEY_SEED_QUERIES.issubset(set(seed_queries)))

        expand_queries = bucket.get("expand_queries")
        self.assertIsInstance(expand_queries, list, "expand_queries must be a list")
        self.assertTrue(all(isinstance(item, str) for item in expand_queries), "expand_queries entries must be strings")
        self.assertTrue(KEY_EXPAND_QUERIES.issubset(set(expand_queries)))

        exclude_terms = bucket.get("exclude_terms")
        self.assertIsInstance(exclude_terms, list, "exclude_terms must be a list")
        self.assertTrue(all(isinstance(item, str) for item in exclude_terms), "exclude_terms entries must be strings")
        self.assertTrue(KEY_EXCLUDE_TERMS.issubset(set(exclude_terms)))

    def test_harbor_fit_rules_structure(self):
        fit_rules = load_harbor_fit_rules()
        self.assertIsInstance(fit_rules, dict, "harbor_fit_rules.yaml must contain a mapping")

        rules = fit_rules.get("harbor_fit_rules")
        self.assertIsInstance(rules, dict, "top-level harbor_fit_rules key must be present")

        axes = ("capability_boundary", "environment_reproducibility", "verifier_stability")
        for axis in axes:
            axis_entry = rules.get(axis)
            self.assertIsInstance(axis_entry, dict, f"{axis} must be a mapping")
            for polarity in ("positive_signals", "negative_signals"):
                signals = axis_entry.get(polarity)
                self.assertIsInstance(signals, list, f"{axis}.{polarity} must be a list")
                self.assertTrue(all(isinstance(item, str) for item in signals), f"{axis}.{polarity} entries must be strings")


class RunBucketSearchHelpersTest(unittest.TestCase):
    def setUp(self):
        self.fixtures_root = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "skill_bundles"

    def test_select_bucket_config_data_quality(self):
        bucket = run_bucket_search.select_bucket_config(CONFIG_PATH, "data-quality")
        self.assertIsInstance(bucket, dict)
        self.assertEqual(bucket.get("slug"), "data-quality")
        self.assertEqual(bucket.get("domain"), "data-ml-engineering")

    def test_select_bucket_config_invalid_top_level(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp:
            tmp.write("[]")
            tmp.flush()
            tmp_path = Path(tmp.name)
        try:
            with self.assertRaises(ValueError) as ctx:
                run_bucket_search.select_bucket_config(tmp_path, "data-quality")
            self.assertIn("top-level mapping", str(ctx.exception))
        finally:
            tmp_path.unlink()

    def test_materialize_selected_results_creates_manifest_and_copies(self):
        bucket_slug = "data-quality"
        selected = sample_selected_entries(self.fixtures_root)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            manifest = run_bucket_search.materialize_selected_results(
                selected, tmp_root, bucket_slug=bucket_slug
            )
            bucket_dir = tmp_root / bucket_slug
            self.assertTrue(bucket_dir.exists())
            manifest_path = bucket_dir / "selected_manifest.yaml"
            self.assertTrue(manifest_path.exists())
            persisted = yaml.safe_load(manifest_path.read_text())
            self.assertEqual(manifest, persisted)
            self.assertEqual(len(persisted), len(selected))
            for idx, entry in enumerate(persisted):
                expected = selected[idx]
                self.assertEqual(entry["rank"], expected["rank"])
                self.assertEqual(entry["id"], expected["id"])
                self.assertEqual(entry["name"], expected["name"])
                self.assertEqual(entry["author"], expected["author"])
                self.assertEqual(entry["skillsmp_url"], expected["skillsmp_url"])
                self.assertEqual(entry["github_url"], expected["github_url"])
                selected_dir = f"{entry['rank']:02d}__{entry['id']}"
                self.assertEqual(entry["selected_dir"], selected_dir)
                copied_dir = bucket_dir / selected_dir
                self.assertTrue(copied_dir.exists())
                self.assertTrue((copied_dir / "SKILL.md").exists())
            dir_names = {item.name for item in bucket_dir.iterdir() if item.is_dir()}
            expected_dirs = {entry["selected_dir"] for entry in manifest}
            self.assertEqual(dir_names, expected_dirs)

    def test_materialize_selected_results_cleans_bucket_dir_on_rerun(self):
        bucket_slug = "data-quality"
        selected_first = sample_selected_entries(self.fixtures_root)
        selected_second = [selected_first[0]]
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            first_manifest = run_bucket_search.materialize_selected_results(
                selected_first, tmp_root, bucket_slug=bucket_slug
            )
            bucket_dir = tmp_root / bucket_slug
            self.assertTrue((bucket_dir / first_manifest[0]["selected_dir"]).exists())
            second_manifest = run_bucket_search.materialize_selected_results(
                selected_second, tmp_root, bucket_slug=bucket_slug
            )
            removed_dir = first_manifest[1]["selected_dir"]
            self.assertFalse((bucket_dir / removed_dir).exists())
            dir_names = {item.name for item in bucket_dir.iterdir() if item.is_dir()}
            expected = {entry["selected_dir"] for entry in second_manifest}
            self.assertEqual(dir_names, expected)

    def test_materialize_selected_results_rejects_unsafe_paths(self):
        bucket_slug = "data-quality"
        selected = sample_selected_entries(self.fixtures_root)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            with self.assertRaises(ValueError):
                run_bucket_search.materialize_selected_results(
                    selected, tmp_root, bucket_slug="../escape"
                )
            invalid_selected = sample_selected_entries(self.fixtures_root)
            invalid_selected[0]["id"] = "../escape"
            with self.assertRaises(ValueError):
                run_bucket_search.materialize_selected_results(
                    invalid_selected, tmp_root, bucket_slug=bucket_slug
                )

    def test_materialize_selected_results_rejects_invalid_rank(self):
        bucket_slug = "data-quality"
        selected = sample_selected_entries(self.fixtures_root)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            selected[0]["rank"] = 0
            with self.assertRaises(ValueError):
                run_bucket_search.materialize_selected_results(
                    selected, tmp_root, bucket_slug=bucket_slug
                )
            selected[0]["rank"] = "../escape"
            with self.assertRaises(ValueError):
                run_bucket_search.materialize_selected_results(
                    selected, tmp_root, bucket_slug=bucket_slug
                )

    def test_resolve_auth_token_skips_blank_bucket_values(self):
        previous_token = os.environ.pop("SKILLSMP_API_KEY", None)
        if previous_token is not None:
            self.addCleanup(lambda: os.environ.__setitem__("SKILLSMP_API_KEY", previous_token))
        else:
            self.addCleanup(lambda: os.environ.pop("SKILLSMP_API_KEY", None))
        bucket = {"auth_token": "   ", "api_key": "   trimmed-token  "}
        token = run_bucket_search._resolve_auth_token(bucket)
        self.assertEqual("trimmed-token", token)

    def test_evaluate_bundle_supports_new_signature_with_bucket_slug(self):
        calls: list[tuple[str, str]] = []

        def evaluate(bundle_dir, *, bucket_slug=None):
            calls.append((str(bundle_dir), bucket_slug))
            return {"selected": True}

        result = run_bucket_search._evaluate_bundle(evaluate, "/tmp/bundle", "data-quality")

        self.assertEqual(result, {"selected": True})
        self.assertEqual(calls, [("/tmp/bundle", "data-quality")])

    def test_evaluate_bundle_supports_legacy_signature_without_bucket_slug(self):
        calls: list[str] = []

        def evaluate(bundle_dir):
            calls.append(str(bundle_dir))
            return {"selected": False}

        result = run_bucket_search._evaluate_bundle(evaluate, "/tmp/bundle", "data-quality")

        self.assertEqual(result, {"selected": False})
        self.assertEqual(calls, ["/tmp/bundle"])

    def test_assert_bucket_review_ready_accepts_any_bucket_when_shared_enabled(self):
        shared_rule = {
            "enabled": True,
            "summary": "shared rubric",
            "keep_rules": [{"id": "bucket_fit", "text": "fit", "required": True}],
            "drop_rules": [{"id": "meta_only", "text": "meta"}],
            "preferred_model": "gpt-5.4",
            "max_markdown_files": 1,
            "max_total_characters": 2000,
        }

        with patch.object(
            run_bucket_search.evaluate_harbor_fit,
            "load_bucket_review_rules",
            return_value={"_shared": shared_rule},
        ):
            run_bucket_search._assert_bucket_review_ready("any-future-bucket")


class RunBucketSearchFlowIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.bucket_config = run_bucket_search.select_bucket_config(CONFIG_PATH, "data-quality")
        self.previous_token = os.environ.get("SKILLSMP_API_KEY")
        os.environ["SKILLSMP_API_KEY"] = "fake-token"
        self.addCleanup(self._restore_token)

    def _restore_token(self):
        if self.previous_token is None:
            os.environ.pop("SKILLSMP_API_KEY", None)
        else:
            os.environ["SKILLSMP_API_KEY"] = self.previous_token

    @staticmethod
    def _fake_review(bundle_dir, *, bucket_slug=None, review_client=None):
        skill_id = Path(bundle_dir).name.split("__", 1)[1]
        selected = "exclude" not in skill_id and "registry" not in skill_id
        return {
            "selected": selected,
            "decision": "keep" if selected else "drop",
            "summary": f"{'keep' if selected else 'drop'} {skill_id}",
            "matched_keep_rules": [],
            "matched_drop_rules": [],
            "confidence": "high",
        }

    def test_run_bucket_flow_materializes_selected_bundle(self):
        def fake_search(scraper, config):
            return [
                {
                    "id": "dq-selected",
                    "name": "Data Quality Selected",
                    "author": "QA Team",
                    "github_url": "https://github.com/example/dq-selected/tree/main/skills/dq-selected",
                    "skillsmp_url": "https://skillsmp.com/skills/dq-selected",
                },
                {
                    "id": "dq-exclude",
                    "name": "Registry Sketch",
                    "author": "Registry Guild",
                    "github_url": "https://github.com/example/dq-exclude/tree/main/skills/dq-exclude",
                    "skillsmp_url": "https://skillsmp.com/skills/dq-exclude",
                },
            ]

        def fake_fetch(scraper, ref):
            skill_slug = Path(ref.path).name
            if skill_slug == "dq-selected":
                content = (
                    "data Objective clarity and schema scope show data engineering ownership "
                    "for deterministic configuration with explicitly specified resources, "
                    "explicit thresholds, and automated checks."
                )
            else:
                content = "registry dependency focus with no reproducible controls."
            return [{"path": "SKILL.md", "content": content}]

        with tempfile.TemporaryDirectory() as download_dir, tempfile.TemporaryDirectory() as results_dir:
            manifest = run_bucket_search.run_bucket_flow(
                bucket_slug="data-quality",
                bucket_config=self.bucket_config,
                download_root=download_dir,
                results_root=results_dir,
                search_scraper_factory=lambda: None,
                fetch_scraper_factory=lambda: None,
                search_fn=fake_search,
                fetch_files_fn=fake_fetch,
                evaluate_fn=self._fake_review,
            )
            bucket_dir = Path(results_dir) / "data-quality"
            manifest_path = bucket_dir / "selected_manifest.yaml"
            self.assertTrue(manifest_path.exists())
            persisted = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest), 1)
            self.assertEqual(manifest, persisted)
            self.assertEqual(manifest[0]["id"], "dq-selected")
            self.assertEqual(persisted[0]["id"], "dq-selected")
            download_bucket = Path(download_dir) / "data-quality"
            self.assertTrue((download_bucket / "01__dq-selected").exists())
            self.assertTrue((download_bucket / "02__dq-exclude").exists())

    def test_run_bucket_flow_continues_when_one_candidate_fetch_fails(self):
        def fake_search(scraper, config):
            return [
                {
                    "id": "dq-selected",
                    "name": "Data Quality Selected",
                    "author": "QA Team",
                    "github_url": "https://github.com/example/dq-selected/tree/main/skills/dq-selected",
                    "skillsmp_url": "https://skillsmp.com/skills/dq-selected",
                },
                {
                    "id": "dq-timeout",
                    "name": "Slow Bundle",
                    "author": "Net Team",
                    "github_url": "https://github.com/example/dq-timeout/tree/main/skills/dq-timeout",
                    "skillsmp_url": "https://skillsmp.com/skills/dq-timeout",
                },
                {
                    "id": "dq-selected-2",
                    "name": "Data Quality Selected 2",
                    "author": "QA Team",
                    "github_url": "https://github.com/example/dq-selected-2/tree/main/skills/dq-selected-2",
                    "skillsmp_url": "https://skillsmp.com/skills/dq-selected-2",
                },
            ]

        def fake_fetch(scraper, ref):
            skill_slug = Path(ref.path).name
            if skill_slug == "dq-timeout":
                raise run_bucket_search.fetch_skill_bundle.FetchSkillBundleError("timed out")
            content = (
                "data quality dataset schema constraints with Great Expectations and dbt tests; "
                "same validation runs in ci/cd with versioned files and automated checks."
            )
            return [{"path": "SKILL.md", "content": content}]

        with tempfile.TemporaryDirectory() as download_dir, tempfile.TemporaryDirectory() as results_dir:
            manifest = run_bucket_search.run_bucket_flow(
                bucket_slug="data-quality",
                bucket_config=self.bucket_config,
                download_root=download_dir,
                results_root=results_dir,
                search_scraper_factory=lambda: None,
                fetch_scraper_factory=lambda: None,
                search_fn=fake_search,
                fetch_files_fn=fake_fetch,
                evaluate_fn=self._fake_review,
            )
            selected_ids = [entry["id"] for entry in manifest]
            self.assertEqual(selected_ids, ["dq-selected", "dq-selected-2"])

    def test_run_bucket_flow_recovers_candidate_when_later_page_backfills_github_url(self):
        bucket_config = dict(self.bucket_config)
        bucket_config["seed_queries"] = ["data quality"]
        bucket_config["expand_queries"] = []
        bucket_config["candidate_limit"] = 5
        bucket_config["selected_target"] = 1
        bucket_config["max_pages_per_query"] = 2
        bucket_config["max_empty_page_streak"] = 1

        page_map = {
            ("data quality", 1): [
                {
                    "id": "dq-backfill",
                    "name": "Data Quality Backfill",
                    "author": "QA Team",
                    "description": "first page misses github url",
                    "github_url": "",
                    "skillsmp_url": "https://skillsmp.com/skills/dq-backfill",
                    "stars": 5,
                    "forks": 1,
                    "queries": ["data quality"],
                }
            ],
            ("data quality", 2): [
                {
                    "id": "dq-backfill",
                    "name": "Data Quality Backfill",
                    "author": "QA Team",
                    "description": "second page includes github url",
                    "github_url": "https://github.com/example/repo/tree/main/skills/dq-backfill",
                    "skillsmp_url": "https://skillsmp.com/skills/dq-backfill",
                    "stars": 8,
                    "forks": 2,
                    "queries": ["data quality"],
                }
            ],
        }

        def fake_search_one_query(scraper, query, limit, page, auth_token=None, url_patterns=None):
            return list(page_map.get((query, page), []))

        def fake_fetch(scraper, ref):
            skill_id = Path(ref.path).name
            return [{"path": "SKILL.md", "content": f"bundle for {skill_id}"}]

        def fake_evaluate(bundle_dir, *, bucket_slug=None, review_client=None):
            return {
                "selected": True,
                "decision": "keep",
                "summary": "keep dq-backfill",
                "matched_keep_rules": [],
                "matched_drop_rules": [],
                "confidence": "high",
            }

        with patch("top20_search.src.search_skillsmp.search_one_query", side_effect=fake_search_one_query):
            with tempfile.TemporaryDirectory() as download_dir, tempfile.TemporaryDirectory() as results_dir:
                manifest = run_bucket_search.run_bucket_flow(
                    bucket_slug="data-quality",
                    bucket_config=bucket_config,
                    download_root=download_dir,
                    results_root=results_dir,
                    search_scraper_factory=lambda: None,
                    fetch_scraper_factory=lambda: None,
                    fetch_files_fn=fake_fetch,
                    evaluate_fn=fake_evaluate,
                )

        self.assertEqual([entry["id"] for entry in manifest], ["dq-backfill"])
        self.assertEqual([entry["rank"] for entry in manifest], [1])

    def test_run_bucket_flow_cleans_download_bucket_before_new_run(self):
        def fake_search(scraper, config):
            return [
                {
                    "id": "dq-selected",
                    "name": "Data Quality Selected",
                    "author": "QA Team",
                    "github_url": "https://github.com/example/dq-selected/tree/main/skills/dq-selected",
                    "skillsmp_url": "https://skillsmp.com/skills/dq-selected",
                }
            ]

        def fake_fetch(scraper, ref):
            content = (
                "data quality dataset schema constraints with Great Expectations and dbt tests; "
                "same validation runs in ci/cd with versioned files and automated checks."
            )
            return [{"path": "SKILL.md", "content": content}]

        with tempfile.TemporaryDirectory() as download_dir, tempfile.TemporaryDirectory() as results_dir:
            stale_dir = Path(download_dir) / "data-quality" / "99__stale-skill"
            stale_dir.mkdir(parents=True, exist_ok=True)
            (stale_dir / "SKILL.md").write_text("stale", encoding="utf-8")

            manifest = run_bucket_search.run_bucket_flow(
                bucket_slug="data-quality",
                bucket_config=self.bucket_config,
                download_root=download_dir,
                results_root=results_dir,
                search_scraper_factory=lambda: None,
                fetch_scraper_factory=lambda: None,
                search_fn=fake_search,
                fetch_files_fn=fake_fetch,
                evaluate_fn=self._fake_review,
            )

            self.assertEqual(len(manifest), 1)
            self.assertFalse(stale_dir.exists())
            download_bucket = Path(download_dir) / "data-quality"
            dir_names = sorted(item.name for item in download_bucket.iterdir() if item.is_dir())
            self.assertEqual(dir_names, ["01__dq-selected"])

    def test_run_bucket_flow_keeps_fetching_until_selected_target(self):
        bucket_config = dict(self.bucket_config)
        bucket_config["selected_target"] = 20

        def make_candidate(skill_id: str):
            return {
                "id": skill_id,
                "name": skill_id,
                "author": "QA Team",
                "github_url": f"https://github.com/example/repo/tree/main/skills/{skill_id}",
                "skillsmp_url": f"https://skillsmp.com/skills/{skill_id}",
            }

        candidates = [make_candidate("skill-01"), make_candidate("skill-01")]
        candidates.extend(make_candidate(f"skill-{index:02d}") for index in range(2, 22))

        fetched_ids: list[str] = []
        evaluated_ids: list[str] = []

        def fake_fetch(scraper, ref):
            skill_id = Path(ref.path).name
            fetched_ids.append(skill_id)
            return [{"path": "SKILL.md", "content": f"bundle for {skill_id}"}]

        def fake_evaluate(bundle_dir, *, bucket_slug=None, review_client=None):
            skill_id = Path(bundle_dir).name.split("__", 1)[1]
            evaluated_ids.append(skill_id)
            return {
                "selected": True,
                "decision": "keep",
                "summary": f"keep {skill_id}",
                "matched_keep_rules": [],
                "matched_drop_rules": [],
                "confidence": "high",
            }

        with tempfile.TemporaryDirectory() as download_dir, tempfile.TemporaryDirectory() as results_dir:
            manifest = run_bucket_search.run_bucket_flow(
                bucket_slug="data-quality",
                bucket_config=bucket_config,
                download_root=download_dir,
                results_root=results_dir,
                search_scraper_factory=lambda: None,
                fetch_scraper_factory=lambda: None,
                search_fn=lambda scraper, config: iter(candidates),
                parse_tree_fn=lambda url: run_bucket_search.fetch_skill_bundle.parse_github_tree_url(url),
                fetch_files_fn=fake_fetch,
                evaluate_fn=fake_evaluate,
            )

        self.assertEqual(len(manifest), 20)
        self.assertEqual([entry["id"] for entry in manifest], [f"skill-{index:02d}" for index in range(1, 21)])
        self.assertEqual(fetched_ids, [f"skill-{index:02d}" for index in range(1, 21)])
        self.assertEqual(evaluated_ids, [f"skill-{index:02d}" for index in range(1, 21)])
        self.assertNotIn("skill-21", fetched_ids)

    def test_candidates_exhausted_returns_partial_manifest(self):
        bucket_config = dict(self.bucket_config)
        bucket_config["selected_target"] = 3

        candidates = [
            {
                "id": "skill-01",
                "name": "skill-01",
                "author": "QA Team",
                "github_url": "https://github.com/example/repo/tree/main/skills/skill-01",
                "skillsmp_url": "https://skillsmp.com/skills/skill-01",
            },
            {
                "id": "skill-02",
                "name": "skill-02",
                "author": "QA Team",
                "github_url": "https://github.com/example/repo/tree/main/skills/skill-02",
                "skillsmp_url": "https://skillsmp.com/skills/skill-02",
            },
            {
                "id": "skill-03",
                "name": "skill-03",
                "author": "QA Team",
                "github_url": "https://github.com/example/repo/tree/main/skills/skill-03",
                "skillsmp_url": "https://skillsmp.com/skills/skill-03",
            },
        ]

        def fake_fetch(scraper, ref):
            skill_id = Path(ref.path).name
            return [{"path": "SKILL.md", "content": f"bundle for {skill_id}"}]

        def fake_evaluate(bundle_dir, *, bucket_slug=None, review_client=None):
            skill_id = Path(bundle_dir).name.split("__", 1)[1]
            selected = skill_id in {"skill-01", "skill-03"}
            return {
                "selected": selected,
                "decision": "keep" if selected else "drop",
                "summary": f"{'keep' if selected else 'drop'} {skill_id}",
                "matched_keep_rules": [],
                "matched_drop_rules": [],
                "confidence": "high",
            }

        with tempfile.TemporaryDirectory() as download_dir, tempfile.TemporaryDirectory() as results_dir:
            manifest = run_bucket_search.run_bucket_flow(
                bucket_slug="data-quality",
                bucket_config=bucket_config,
                download_root=download_dir,
                results_root=results_dir,
                search_scraper_factory=lambda: None,
                fetch_scraper_factory=lambda: None,
                search_fn=lambda scraper, config: iter(candidates),
                parse_tree_fn=lambda url: run_bucket_search.fetch_skill_bundle.parse_github_tree_url(url),
                fetch_files_fn=fake_fetch,
                evaluate_fn=fake_evaluate,
            )

        self.assertEqual([entry["id"] for entry in manifest], ["skill-01", "skill-03"])
        self.assertEqual([entry["rank"] for entry in manifest], [1, 2])
        self.assertEqual([entry["selected_dir"] for entry in manifest], ["01__skill-01", "02__skill-03"])

    def test_run_bucket_flow_accepts_shared_rule_bucket(self):
        xlsx_bucket = run_bucket_search.select_bucket_config(CONFIG_PATH, "xlsx")

        with tempfile.TemporaryDirectory() as download_dir, tempfile.TemporaryDirectory() as results_dir:
            manifest = run_bucket_search.run_bucket_flow(
                bucket_slug="xlsx",
                bucket_config=xlsx_bucket,
                download_root=download_dir,
                results_root=results_dir,
                search_scraper_factory=lambda: None,
                fetch_scraper_factory=lambda: None,
                search_fn=lambda scraper, config: iter([]),
            )
        self.assertEqual(manifest, [])

    def test_run_bucket_flow_dedupes_selected_skill_identity(self):
        bucket_config = dict(self.bucket_config)
        bucket_config["selected_target"] = 2

        def fake_search(scraper, config):
            return [
                {
                    "id": "dup-en",
                    "name": "Duplicate EN",
                    "author": "dup-author",
                    "github_url": "https://github.com/example/repo/tree/main/skills/dup-en",
                    "skillsmp_url": "https://skillsmp.com/skills/dup-en",
                },
                {
                    "id": "dup-ko",
                    "name": "Duplicate KO",
                    "author": "dup-author",
                    "github_url": "https://github.com/example/repo/tree/main/skills/dup-ko",
                    "skillsmp_url": "https://skillsmp.com/skills/dup-ko",
                },
                {
                    "id": "unique-skill",
                    "name": "Unique Skill",
                    "author": "other-author",
                    "github_url": "https://github.com/example/repo/tree/main/skills/unique-skill",
                    "skillsmp_url": "https://skillsmp.com/skills/unique-skill",
                },
            ]

        def fake_fetch(scraper, ref):
            skill_slug = Path(ref.path).name
            if skill_slug in {"dup-en", "dup-ko"}:
                return [
                    {
                        "path": "SKILL.md",
                        "content": "---\nname: repeated-skill\nauthor: dup-author\n---\n\n# Duplicate\n",
                    }
                ]
            return [
                {
                    "path": "SKILL.md",
                    "content": "---\nname: unique-skill\nauthor: other-author\n---\n\n# Unique\n",
                }
            ]

        def fake_evaluate(bundle_dir, *, bucket_slug=None, review_client=None):
            return {
                "selected": True,
                "decision": "keep",
                "summary": "keep",
                "matched_keep_rules": [],
                "matched_drop_rules": [],
                "confidence": "high",
            }

        with tempfile.TemporaryDirectory() as download_dir, tempfile.TemporaryDirectory() as results_dir:
            manifest = run_bucket_search.run_bucket_flow(
                bucket_slug="data-quality",
                bucket_config=bucket_config,
                download_root=download_dir,
                results_root=results_dir,
                search_scraper_factory=lambda: None,
                fetch_scraper_factory=lambda: None,
                search_fn=fake_search,
                fetch_files_fn=fake_fetch,
                evaluate_fn=fake_evaluate,
            )

        self.assertEqual([entry["id"] for entry in manifest], ["dup-en", "unique-skill"])


class RunBucketSearchCLITest(unittest.TestCase):
    def setUp(self):
        self.previous_token = os.environ.get("SKILLSMP_API_KEY")
        os.environ["SKILLSMP_API_KEY"] = "cli-token"
        self.addCleanup(self._restore_token)

    def _restore_token(self):
        if self.previous_token is None:
            os.environ.pop("SKILLSMP_API_KEY", None)
        else:
            os.environ["SKILLSMP_API_KEY"] = self.previous_token

    def test_main_exits_cleanly_on_missing_config(self):
        fake_path = Path(tempfile.gettempdir()) / "missing-bucket-config.yaml"
        fake_path.unlink(missing_ok=True)
        with self.assertRaises(SystemExit) as ctx:
            run_bucket_search.main(["--config-path", str(fake_path), "--bucket-slug", "data-quality"])
        self.assertIn("config not found", str(ctx.exception))

    def test_main_runs_shared_rule_bucket(self):
        with patch("top20_search.src.run_bucket_search.run_bucket_flow", return_value=[]) as mocked_run:
            run_bucket_search.main(["--config-path", str(CONFIG_PATH), "--bucket-slug", "xlsx"])
        self.assertEqual(mocked_run.call_count, 1)
