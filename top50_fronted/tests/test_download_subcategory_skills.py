from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

import yaml

from src.download_subcategory_skills import (
    collect_skill_records,
    list_category_dirs_until,
    parse_args,
    run_download_flow,
)
from top20_search.src.fetch_skill_bundle import FetchSkillBundleError, GitHubTreeRef, ParsedGitHubDirectory


class DownloadSubcategorySkillsTests(unittest.TestCase):
    def _write_snapshot(self, path: Path, *, subcategory_slug: str, skills: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(
                {
                    "subcategory_slug": subcategory_slug,
                    "skills": skills,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    def test_list_category_dirs_until_includes_end_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            for name in ("blockchain", "business", "development", "devops", "tools"):
                (base_dir / name).mkdir()

            selected = list_category_dirs_until(base_dir, "development")

        self.assertEqual([path.name for path in selected], ["blockchain", "business", "development"])

    def test_collect_skill_records_reads_yaml_files_until_end_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            self._write_snapshot(
                base_dir / "blockchain" / "defi.yaml",
                subcategory_slug="defi",
                skills=[
                    {"rank": 1, "id": "skill-a", "name": "Skill A", "author": "alice", "github_url": "https://github.com/example/repo/tree/main/skills/skill-a"},
                ],
            )
            self._write_snapshot(
                base_dir / "development" / "frontend.yaml",
                subcategory_slug="frontend",
                skills=[
                    {"rank": 2, "id": "skill-b", "name": "Skill B", "author": "bob", "github_url": "https://github.com/example/repo/tree/main/skills/skill-b"},
                ],
            )
            self._write_snapshot(
                base_dir / "devops" / "cloud.yaml",
                subcategory_slug="cloud",
                skills=[
                    {"rank": 3, "id": "skill-c", "name": "Skill C", "author": "carol", "github_url": "https://github.com/example/repo/tree/main/skills/skill-c"},
                ],
            )

            records, included_categories = collect_skill_records(base_dir, "development")

        self.assertEqual(included_categories, ["blockchain", "development"])
        self.assertEqual([(record["subcategory_slug"], record["id"]) for record in records], [("defi", "skill-a"), ("frontend", "skill-b")])

    def test_parse_args_accepts_jobs(self) -> None:
        args = parse_args(["--jobs", "6"])
        self.assertEqual(args.jobs, 6)

    def test_run_download_flow_dedupes_network_fetch_and_materializes_each_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "input"
            output_dir = Path(tmp_dir) / "output"
            shared_url = "https://github.com/example/repo/tree/main/skills/shared"
            self._write_snapshot(
                input_dir / "blockchain" / "defi.yaml",
                subcategory_slug="defi",
                skills=[
                    {"rank": 1, "id": "shared-one", "name": "Shared One", "author": "alice", "github_url": shared_url},
                ],
            )
            self._write_snapshot(
                input_dir / "development" / "frontend.yaml",
                subcategory_slug="frontend",
                skills=[
                    {"rank": 2, "id": "shared-two", "name": "Shared Two", "author": "bob", "github_url": shared_url},
                ],
            )
            fetch_calls: list[str] = []

            def parse_url(url: str, **_: object) -> ParsedGitHubDirectory:
                return ParsedGitHubDirectory(
                    url_kind="tree",
                    ref=GitHubTreeRef("example", "repo", "main", "skills/shared"),
                )

            def fetch_tree(ref: GitHubTreeRef) -> list[dict[str, str]]:
                fetch_calls.append(f"{ref.owner}/{ref.repo}/{ref.path}")
                return [{"path": "SKILL.md", "content": "---\nslug: shared\n---\n"}]

            logs: list[str] = []
            manifest = run_download_flow(
                input_dir=input_dir,
                end_category="development",
                output_dir=output_dir,
                jobs=1,
                parse_url_fn=parse_url,
                fetch_tree_files_fn=fetch_tree,
                log_fn=logs.append,
            )

            self.assertEqual(fetch_calls, ["example/repo/skills/shared"])
            self.assertEqual(manifest["stats"]["downloaded"], 2)
            self.assertEqual(manifest["stats"]["cache_hits"], 1)
            self.assertTrue((output_dir / "blockchain" / "defi" / "01__Shared One" / "SKILL.md").exists())
            self.assertTrue((output_dir / "development" / "frontend" / "02__Shared Two" / "SKILL.md").exists())
            self.assertEqual([entry["cache_hit"] for entry in manifest["entries"]], [False, True])
            self.assertTrue((output_dir / "download_manifest.yaml").exists())
            self.assertTrue(any("manifest_path" in line for line in logs))

    def test_run_download_flow_marks_repo_root_without_skill_markdown_as_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "input"
            output_dir = Path(tmp_dir) / "output"
            self._write_snapshot(
                input_dir / "development" / "frontend.yaml",
                subcategory_slug="frontend",
                skills=[
                    {"rank": 1, "id": "root-skill", "name": "Root Skill", "author": "alice", "github_url": "https://github.com/example/root-skill"},
                ],
            )

            def parse_url(url: str, **_: object) -> ParsedGitHubDirectory:
                return ParsedGitHubDirectory(
                    url_kind="repo_root",
                    ref=GitHubTreeRef("example", "root-skill", "main", ""),
                )

            manifest = run_download_flow(
                input_dir=input_dir,
                end_category="development",
                output_dir=output_dir,
                parse_url_fn=parse_url,
                fetch_repo_root_files_fn=lambda ref: (_ for _ in ()).throw(
                    FetchSkillBundleError(
                        f"Downloaded GitHub directory is missing SKILL.md/skill.md: {ref.owner}/{ref.repo}/{ref.path}@{ref.branch}"
                    )
                ),
                log_fn=lambda _: None,
            )

            self.assertEqual(manifest["stats"]["skipped"], 1)
            self.assertEqual(manifest["entries"][0]["status"], "skipped")
            self.assertEqual(manifest["entries"][0]["url_kind"], "repo_root")
            self.assertFalse((output_dir / "development" / "frontend" / "01__Root Skill").exists())

    def test_run_download_flow_marks_download_error_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "input"
            output_dir = Path(tmp_dir) / "output"
            self._write_snapshot(
                input_dir / "development" / "frontend.yaml",
                subcategory_slug="frontend",
                skills=[
                    {"rank": 1, "id": "tree-skill", "name": "Tree Skill", "author": "alice", "github_url": "https://github.com/example/repo/tree/main/skills/tree-skill"},
                ],
            )

            def parse_url(url: str, **_: object) -> ParsedGitHubDirectory:
                return ParsedGitHubDirectory(
                    url_kind="tree",
                    ref=GitHubTreeRef("example", "repo", "main", "skills/tree-skill"),
                )

            manifest = run_download_flow(
                input_dir=input_dir,
                end_category="development",
                output_dir=output_dir,
                parse_url_fn=parse_url,
                fetch_tree_files_fn=lambda _ref: (_ for _ in ()).throw(
                    FetchSkillBundleError("GitHub contents API request failed for example/repo")
                ),
                log_fn=lambda _: None,
            )

            self.assertEqual(manifest["stats"]["failed"], 1)
            self.assertEqual(manifest["entries"][0]["status"], "failed")
            self.assertEqual(manifest["entries"][0]["url_kind"], "tree")
            self.assertFalse((output_dir / "development" / "frontend" / "01__Tree Skill").exists())

    def test_run_download_flow_falls_back_to_rank_when_skill_name_is_not_usable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "input"
            output_dir = Path(tmp_dir) / "output"
            self._write_snapshot(
                input_dir / "development" / "frontend.yaml",
                subcategory_slug="frontend",
                skills=[
                    {"rank": 1, "id": "bad-name", "name": "bad/name", "author": "alice", "github_url": "https://github.com/example/repo/tree/main/skills/bad-name"},
                ],
            )

            def parse_url(url: str, **_: object) -> ParsedGitHubDirectory:
                return ParsedGitHubDirectory(
                    url_kind="tree",
                    ref=GitHubTreeRef("example", "repo", "main", "skills/bad-name"),
                )

            manifest = run_download_flow(
                input_dir=input_dir,
                end_category="development",
                output_dir=output_dir,
                parse_url_fn=parse_url,
                fetch_tree_files_fn=lambda _ref: [{"path": "SKILL.md", "content": "---\nslug: bad-name\n---\n"}],
                log_fn=lambda _: None,
            )

            self.assertEqual(manifest["stats"]["downloaded"], 1)
            self.assertTrue((output_dir / "development" / "frontend" / "01" / "SKILL.md").exists())
            self.assertFalse((output_dir / "development" / "frontend" / "01__bad/name").exists())

    def test_run_download_flow_keeps_manifest_entry_order_when_parallel_finishes_out_of_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "input"
            output_dir = Path(tmp_dir) / "output"
            self._write_snapshot(
                input_dir / "blockchain" / "defi.yaml",
                subcategory_slug="defi",
                skills=[
                    {"rank": 1, "id": "slow-skill", "name": "Slow Skill", "author": "alice", "github_url": "https://github.com/example/repo/tree/main/skills/slow-skill"},
                ],
            )
            self._write_snapshot(
                input_dir / "development" / "frontend.yaml",
                subcategory_slug="frontend",
                skills=[
                    {"rank": 2, "id": "fast-skill", "name": "Fast Skill", "author": "bob", "github_url": "https://github.com/example/repo/tree/main/skills/fast-skill"},
                ],
            )

            def parse_url(url: str, **_: object) -> ParsedGitHubDirectory:
                if url.endswith("/slow-skill"):
                    return ParsedGitHubDirectory(
                        url_kind="tree",
                        ref=GitHubTreeRef("example", "repo", "main", "skills/slow-skill"),
                    )
                return ParsedGitHubDirectory(
                    url_kind="tree",
                    ref=GitHubTreeRef("example", "repo", "main", "skills/fast-skill"),
                )

            def fetch_tree(ref: GitHubTreeRef) -> list[dict[str, str]]:
                if ref.path.endswith("slow-skill"):
                    time.sleep(0.15)
                return [{"path": "SKILL.md", "content": f"---\nslug: {ref.path}\n---\n"}]

            manifest = run_download_flow(
                input_dir=input_dir,
                end_category="development",
                output_dir=output_dir,
                jobs=2,
                parse_url_fn=parse_url,
                fetch_tree_files_fn=fetch_tree,
                log_fn=lambda _: None,
            )

            self.assertEqual(
                [entry["id"] for entry in manifest["entries"]],
                ["slow-skill", "fast-skill"],
            )
            self.assertTrue((output_dir / "blockchain" / "defi" / "01__Slow Skill" / "SKILL.md").exists())
            self.assertTrue((output_dir / "development" / "frontend" / "02__Fast Skill" / "SKILL.md").exists())
