import tempfile
import unittest
from pathlib import Path
from unittest import mock
import requests

from top50_search.src.fetch_skill_bundle import (
    FetchSkillBundleError,
    GitHubTreeRef,
    _default_fallback_fetch,
    _fetch_via_github_html_pages,
    build_candidate_download_dir,
    fetch_skill_directory_files,
    parse_github_tree_url,
    safe_relative_path,
    write_downloaded_skill_files,
)


class DummyResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, object],
        headers: dict[str, object] | None = None,
        json_exception: Exception | None = None,
    ):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self._json_exception = json_exception

    def raise_for_status(self) -> None:
        if self.status_code >= 400 and self.status_code != 429:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, object]:
        if self._json_exception:
            raise self._json_exception
        return self._payload


class DummyScraper:
    def __init__(self, responses: list[DummyResponse]):
        self._responses = list(responses)
        self.calls: list[str] = []

    def get(self, url: str, timeout: int, headers: dict[str, str] | None = None) -> DummyResponse:
        self.calls.append(url)
        if not self._responses:
            raise RuntimeError("no responses configured")
        return self._responses.pop(0)


class FetchSkillBundleTests(unittest.TestCase):
    def test_parse_github_tree_url(self) -> None:
        ref = parse_github_tree_url("https://github.com/owner/repo/tree/main/skills/data-quality")
        self.assertEqual(ref.owner, "owner")
        self.assertEqual(ref.repo, "repo")
        self.assertEqual(ref.branch, "main")
        self.assertEqual(ref.path, "skills/data-quality")

    def test_build_candidate_download_dir(self) -> None:
        base = Path("downloads")
        target = build_candidate_download_dir(base, "data-quality", {"rank": 3, "id": "skill-42"})
        self.assertEqual(target, base / "data-quality" / "03__skill-42")

    def test_build_candidate_download_dir_validates_skill_id(self) -> None:
        with self.assertRaises(FetchSkillBundleError):
            build_candidate_download_dir(Path("downloads"), "data-quality", {"rank": 1, "id": "../skill"})
        with self.assertRaises(FetchSkillBundleError):
            build_candidate_download_dir(Path("downloads"), "data-quality", {"rank": 1, "slug": "bad/slug"})

    def test_build_candidate_download_dir_accepts_slug(self) -> None:
        target = build_candidate_download_dir(Path("downloads"), "data-quality", {"rank": 1, "slug": "safe-slug"})
        self.assertEqual(target, Path("downloads") / "data-quality" / "01__safe-slug")

    def test_safe_relative_path_rejects_unsafe(self) -> None:
        with self.assertRaises(FetchSkillBundleError):
            safe_relative_path("../secrets.txt")

    def test_write_downloaded_skill_files_creates_nested(self) -> None:
        files = [
            {"path": "bundle/src/main.py", "content": "print('hello')"},
            {"path": "bundle/README.md", "content": "bundle description"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            written = write_downloaded_skill_files(files, tmpdir)
            expected_top = Path(tmpdir) / "bundle"
            self.assertTrue((expected_top / "src" / "main.py").exists())
            self.assertTrue((expected_top / "README.md").exists())
            self.assertEqual(len(written), 2)
            self.assertEqual((expected_top / "src" / "main.py").read_text(), "print('hello')")

    def test_write_downloaded_skill_files_overwrites_previous_contents(self) -> None:
        first = [{"path": "bundle/old.txt", "content": "old"}]
        second = [{"path": "bundle/new.txt", "content": "new"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            write_downloaded_skill_files(first, tmpdir)
            self.assertTrue((Path(tmpdir) / "bundle" / "old.txt").exists())
            write_downloaded_skill_files(second, tmpdir)
            self.assertFalse((Path(tmpdir) / "bundle" / "old.txt").exists())
            self.assertTrue((Path(tmpdir) / "bundle" / "new.txt").exists())

    def test_fetch_skill_directory_files_retries_then_succeeds(self) -> None:
        responses = [
            DummyResponse(429, {}, headers={"Retry-After": "0.05"}),
            DummyResponse(200, {"files": [{"path": "bundle/README.md", "content": "done"}]}),
        ]
        scraper = DummyScraper(responses)
        ref = GitHubTreeRef("owner", "repo", "main", "skills/data-quality")
        sleep_calls: list[float] = []
        files = fetch_skill_directory_files(
            scraper,
            ref,
            max_retries=2,
            sleep_fn=lambda delay: sleep_calls.append(delay),
        )
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].get("path"), "bundle/README.md")
        self.assertEqual(files[0].get("content"), "done")
        self.assertEqual(len(sleep_calls), 1)
        self.assertAlmostEqual(sleep_calls[0], 0.05, places=3)

    def test_fetch_skill_directory_files_retry_after_invalid_falls_back(self) -> None:
        responses = [
            DummyResponse(429, {}, headers={"Retry-After": "invalid"}),
            DummyResponse(200, {"files": [{"path": "bundle/README.md", "content": "done"}]}),
        ]
        scraper = DummyScraper(responses)
        ref = GitHubTreeRef("owner", "repo", "main", "skills/data-quality")
        sleep_calls: list[float] = []
        fetch_skill_directory_files(
            scraper,
            ref,
            max_retries=2,
            sleep_fn=lambda delay: sleep_calls.append(delay),
        )
        self.assertEqual(len(sleep_calls), 1)
        self.assertAlmostEqual(sleep_calls[0], 1.0, places=3)

    def test_fetch_skill_directory_files_fails_after_retries(self) -> None:
        responses = [
            DummyResponse(429, {}, headers={"Retry-After": "0.01"}),
            DummyResponse(429, {}, headers={"Retry-After": "0.01"}),
        ]
        scraper = DummyScraper(responses)
        ref = GitHubTreeRef("owner", "repo", "main", "skills/data-quality")
        with self.assertRaises(FetchSkillBundleError):
            fetch_skill_directory_files(scraper, ref, max_retries=1, sleep_fn=lambda _: None)

    def test_fetch_skill_directory_files_invalid_payload(self) -> None:
        responses = [DummyResponse(200, {"files": "wrong"})]
        scraper = DummyScraper(responses)
        ref = GitHubTreeRef("owner", "repo", "main", "skills/data-quality")
        with self.assertRaises(FetchSkillBundleError):
            fetch_skill_directory_files(scraper, ref, max_retries=0, sleep_fn=lambda _: None)

    def test_fetch_skill_directory_files_json_error(self) -> None:
        responses = [
            DummyResponse(200, {}, json_exception=ValueError("boom")),
        ]
        scraper = DummyScraper(responses)
        ref = GitHubTreeRef("owner", "repo", "main", "skills/data-quality")
        with self.assertRaises(FetchSkillBundleError):
            fetch_skill_directory_files(scraper, ref, max_retries=0, sleep_fn=lambda _: None)

    def test_fetch_skill_directory_files_falls_back_after_forbidden(self) -> None:
        responses = [DummyResponse(403, {})]
        scraper = DummyScraper(responses)
        ref = GitHubTreeRef("owner", "repo", "main", "skills/data-quality")

        files = fetch_skill_directory_files(
            scraper,
            ref,
            max_retries=0,
            sleep_fn=lambda _: None,
            fallback_fetch_fn=lambda inner_ref, timeout: [
                {"path": "SKILL.md", "content": f"{inner_ref.owner}/{inner_ref.repo}/{inner_ref.path}"}
            ],
        )

        self.assertEqual(files, [{"path": "SKILL.md", "content": "owner/repo/skills/data-quality"}])

    def test_fetch_via_github_html_pages_recovers_markdown_docs(self) -> None:
        tree_html = """
        <html><body>
        <script type="application/json" data-target="react-app.embeddedData">{
          "payload": {
            "codeViewTreeRoute": {
              "tree": {
                "items": [
                  {"name": "SKILL.md", "path": "skills/data-quality/SKILL.md", "contentType": "file"},
                  {"name": "references", "path": "skills/data-quality/references", "contentType": "directory"},
                  {"name": "tool.py", "path": "skills/data-quality/tool.py", "contentType": "file"}
                ]
              }
            }
          }
        }</script>
        </body></html>
        """
        nested_tree_html = """
        <html><body>
        <script type="application/json" data-target="react-app.embeddedData">{
          "payload": {
            "codeViewTreeRoute": {
              "tree": {
                "items": [
                  {"name": "guide.md", "path": "skills/data-quality/references/guide.md", "contentType": "file"}
                ]
              }
            }
          }
        }</script>
        </body></html>
        """
        skill_blob_html = """
        <html><body>
        <script type="application/json" data-target="react-app.embeddedData">{
          "payload": {
            "codeViewBlobRoute": {
              "richText": "<article><h1>Skill Title</h1><p>Deterministic checks.</p></article>"
            }
          }
        }</script>
        </body></html>
        """
        guide_blob_html = """
        <html><body>
        <script type="application/json" data-target="react-app.embeddedData">{
          "payload": {
            "codeViewBlobRoute": {
              "richText": "<article><p>Reference guide.</p></article>"
            }
          }
        }</script>
        </body></html>
        """

        responses = {
            "https://github.com/owner/repo/tree/main/skills/data-quality": tree_html,
            "https://github.com/owner/repo/tree/main/skills/data-quality/references": nested_tree_html,
            "https://github.com/owner/repo/blob/main/skills/data-quality/SKILL.md": skill_blob_html,
            "https://github.com/owner/repo/blob/main/skills/data-quality/references/guide.md": guide_blob_html,
        }

        def fake_get(url: str, headers: dict[str, str], timeout: int):
            if url not in responses:
                raise AssertionError(f"unexpected URL: {url}")

            class Response:
                status_code = 200
                text = responses[url]
                headers = {"content-type": "text/html; charset=utf-8"}

                def raise_for_status(self):
                    return None

            return Response()

        ref = GitHubTreeRef("owner", "repo", "main", "skills/data-quality")
        files = _fetch_via_github_html_pages(ref, timeout=10, requests_get=fake_get)

        self.assertEqual(
            files,
            [
                {"path": "SKILL.md", "content": "Skill Title\n\nDeterministic checks."},
                {"path": "references/guide.md", "content": "Reference guide."},
            ],
        )

    def test_fetch_via_github_html_pages_retries_timeout(self) -> None:
        tree_html = """
        <html><body>
        <script type="application/json" data-target="react-app.embeddedData">{
          "payload": {
            "codeViewTreeRoute": {
              "tree": {
                "items": [
                  {"name": "SKILL.md", "path": "skills/data-quality/SKILL.md", "contentType": "file"}
                ]
              }
            }
          }
        }</script>
        </body></html>
        """
        skill_blob_html = """
        <html><body>
        <script type="application/json" data-target="react-app.embeddedData">{
          "payload": {
            "codeViewBlobRoute": {
              "richText": "<article><p>Recovered after retry.</p></article>"
            }
          }
        }</script>
        </body></html>
        """
        call_counts = {
            "https://github.com/owner/repo/tree/main/skills/data-quality": 0,
            "https://github.com/owner/repo/blob/main/skills/data-quality/SKILL.md": 0,
        }

        def fake_get(url: str, headers: dict[str, str], timeout: int):
            call_counts[url] += 1
            if call_counts[url] == 1:
                raise requests.exceptions.ReadTimeout(f"timeout on {url}")

            class Response:
                status_code = 200
                text = tree_html if "/tree/" in url else skill_blob_html
                headers = {"content-type": "text/html; charset=utf-8"}

                def raise_for_status(self):
                    return None

            return Response()

        ref = GitHubTreeRef("owner", "repo", "main", "skills/data-quality")
        files = _fetch_via_github_html_pages(ref, timeout=10, requests_get=fake_get)

        self.assertEqual(files, [{"path": "SKILL.md", "content": "Recovered after retry."}])

    def test_default_fallback_fetch_uses_sparse_checkout_after_html_failure(self) -> None:
        ref = GitHubTreeRef("owner", "repo", "main", "skills/data-quality")
        expected = [{"path": "SKILL.md", "content": "Recovered via git"}]

        with mock.patch(
            "top50_search.src.fetch_skill_bundle._fetch_via_github_contents_api",
            side_effect=FetchSkillBundleError("contents blocked"),
        ) as contents_mock, mock.patch(
            "top50_search.src.fetch_skill_bundle._fetch_via_github_html_pages",
            side_effect=FetchSkillBundleError("html blocked"),
        ) as html_mock, mock.patch(
            "top50_search.src.fetch_skill_bundle._fetch_via_github_sparse_checkout",
            return_value=expected,
        ) as sparse_mock:
            files = _default_fallback_fetch(ref, timeout=30)

        self.assertEqual(files, expected)
        contents_mock.assert_called_once_with(ref, 30)
        html_mock.assert_called_once_with(ref, 30)
        sparse_mock.assert_called_once_with(ref, 30)
