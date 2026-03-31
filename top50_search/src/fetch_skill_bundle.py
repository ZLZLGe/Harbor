from __future__ import annotations

import base64
import html
from html.parser import HTMLParser
import json
import os
import subprocess
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlencode, urlparse

import requests

SKILLSMP_GITHUB_CONTENTS_URL = "https://skillsmp.com/api/github-contents"
GITHUB_CONTENTS_API_URL = "https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
GITHUB_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Harbor-top50-search",
}
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 5
REACT_EMBEDDED_DATA_MARKER = '<script type="application/json" data-target="react-app.embeddedData">'


class FetchSkillBundleError(RuntimeError):
    """Raised when a bundle fetch operation cannot complete."""


@dataclass(frozen=True)
class GitHubTreeRef:
    owner: str
    repo: str
    branch: str
    path: str


class _RichTextToTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "p", "div", "li", "tr", "table", "article"} or tag.startswith("h"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "li", "tr", "table", "article"} or tag.startswith("h"):
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        lines = [line.strip() for line in raw.splitlines()]
        cleaned: list[str] = []
        previous_blank = False
        for line in lines:
            if not line:
                if not previous_blank:
                    cleaned.append("")
                previous_blank = True
                continue
            cleaned.append(line)
            previous_blank = False
        return "\n".join(cleaned).strip()


def _sanitize_candidate_name(raw_name: str) -> str:
    normalized = raw_name.strip()
    if not normalized:
        raise FetchSkillBundleError("Skill id cannot be empty")
    if "/" in normalized or "\\" in normalized:
        raise FetchSkillBundleError(f"Unsafe skill id segment: {raw_name}")
    posix_path = PurePosixPath(normalized)
    if posix_path.is_absolute():
        raise FetchSkillBundleError(f"Unsafe skill id segment: {raw_name}")
    if any(segment in ("", ".", "..") for segment in posix_path.parts):
        raise FetchSkillBundleError(f"Unsafe skill id segment: {raw_name}")
    if len(posix_path.parts) != 1:
        raise FetchSkillBundleError(f"Unsafe skill id segment: {raw_name}")
    return posix_path.name


def parse_github_tree_url(url: str) -> GitHubTreeRef:
    parsed = urlparse(url)
    if parsed.netloc != "github.com":
        raise FetchSkillBundleError(f"Unsupported GitHub URL: {url}")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 5 or parts[2] != "tree":
        raise FetchSkillBundleError(f"Unable to parse GitHub tree URL: {url}")

    owner, repo, _, branch = parts[:4]
    path = "/".join(parts[4:])
    if not path:
        raise FetchSkillBundleError(f"GitHub tree URL missing skill path: {url}")
    return GitHubTreeRef(owner=owner, repo=repo, branch=branch, path=path)


def build_candidate_download_dir(base_dir: Path | str, bucket_slug: str, skill: dict[str, Any]) -> Path:
    base_path = Path(base_dir)
    rank = int(skill["rank"])
    raw_skill_id = skill.get("id") or skill.get("slug")
    if raw_skill_id is None:
        raise FetchSkillBundleError("Skill is missing an id")
    safe_skill_id = _sanitize_candidate_name(str(raw_skill_id))
    candidate_dir = f"{rank:02d}__{safe_skill_id}"
    return base_path / bucket_slug / candidate_dir


def safe_relative_path(raw_path: str) -> Path:
    posix_path = PurePosixPath(raw_path)
    if posix_path.is_absolute() or ".." in posix_path.parts:
        raise FetchSkillBundleError(f"Unsafe relative path detected: {raw_path}")
    return Path(*posix_path.parts)


def write_downloaded_skill_files(files: list[dict[str, Any]], output_dir: Path | str) -> list[Path]:
    base_dir = Path(output_dir)
    if base_dir.exists():
        if base_dir.is_file():
            base_dir.unlink()
        else:
            shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for file_info in files:
        raw_path = file_info.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise FetchSkillBundleError("Received file entry without a valid path")
        relative_path = safe_relative_path(raw_path)
        target_path = base_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content = file_info.get("content") or ""
        target_path.write_text(str(content), encoding="utf-8")
        written.append(target_path)
    return written


def _compute_retry_delay(headers: dict[str, Any], attempt: int) -> float:
    retry_after = headers.get("Retry-After")
    if retry_after is not None:
        try:
            delay = float(retry_after)
            if delay >= 0:
                return delay
        except (ValueError, TypeError):
            pass
    return min(2 ** attempt, 30.0)


def _github_api_headers() -> dict[str, str]:
    headers = dict(GITHUB_API_HEADERS)
    token = (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
    )
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"
    return headers


def _http_get_with_retries(
    url: str,
    *,
    headers: dict[str, str],
    timeout: int,
    requests_get: Callable[..., Any] = requests.get,
    attempts: int = 3,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return requests_get(url, headers=headers, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
            if attempt < attempts:
                sleep_fn(min(float(attempt), 3.0))
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise FetchSkillBundleError(f"request failed unexpectedly for {url}")


def _extract_react_embedded_data(page_html: str) -> dict[str, Any]:
    start = page_html.find(REACT_EMBEDDED_DATA_MARKER)
    if start == -1:
        raise FetchSkillBundleError("GitHub HTML page missing embedded React data")
    start += len(REACT_EMBEDDED_DATA_MARKER)
    end = page_html.find("</script>", start)
    if end == -1:
        raise FetchSkillBundleError("GitHub HTML page missing embedded React data terminator")
    try:
        return json.loads(page_html[start:end])
    except Exception as exc:
        raise FetchSkillBundleError("GitHub HTML embedded data is not valid JSON") from exc


def _rich_text_html_to_text(rich_text: str) -> str:
    parser = _RichTextToTextParser()
    parser.feed(html.unescape(rich_text))
    return parser.get_text()


def _run_git_command(args: list[str], timeout: int) -> None:
    try:
        subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip()
        raise FetchSkillBundleError(
            f"GitHub fallback command failed: {' '.join(args)}"
            + (f" ({stderr})" if stderr else "")
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise FetchSkillBundleError(
            f"GitHub fallback command timed out after {timeout}s: {' '.join(args)}"
        ) from exc


def _fetch_via_github_sparse_checkout(ref: GitHubTreeRef, timeout: int) -> list[dict[str, Any]]:
    remote_url = f"https://github.com/{ref.owner}/{ref.repo}.git"
    relative_dir = Path(*PurePosixPath(ref.path).parts)
    with tempfile.TemporaryDirectory(prefix="top50-search-git-") as tmpdir:
        repo_dir = Path(tmpdir) / "repo"
        _run_git_command(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                "--branch",
                ref.branch,
                remote_url,
                str(repo_dir),
            ],
            timeout,
        )
        _run_git_command(
            [
                "git",
                "-C",
                str(repo_dir),
                "sparse-checkout",
                "set",
                "--no-cone",
                ref.path,
            ],
            timeout,
        )
        target_dir = repo_dir / relative_dir
        if not target_dir.exists() or not target_dir.is_dir():
            raise FetchSkillBundleError(
                f"GitHub fallback could not find skill directory: {ref.owner}/{ref.repo}/{ref.path}@{ref.branch}"
            )

        files: list[dict[str, Any]] = []
        for candidate in sorted(target_dir.rglob("*")):
            if not candidate.is_file():
                continue
            relative_path = candidate.relative_to(target_dir).as_posix()
            content = candidate.read_text(encoding="utf-8", errors="ignore")
            files.append({"path": relative_path, "content": content})
        return files


def _fetch_via_github_contents_api(ref: GitHubTreeRef, timeout: int) -> list[dict[str, Any]]:
    root_path = PurePosixPath(ref.path)
    queue = [ref.path]
    files: list[dict[str, Any]] = []

    while queue:
        current_path = queue.pop(0)
        url = GITHUB_CONTENTS_API_URL.format(
            owner=ref.owner,
            repo=ref.repo,
            path=current_path,
            branch=ref.branch,
        )
        try:
            response = requests.get(url, headers=_github_api_headers(), timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise FetchSkillBundleError(
                f"GitHub contents API request failed for {ref.owner}/{ref.repo}/{current_path}@{ref.branch}"
            ) from exc
        if not isinstance(payload, list):
            raise FetchSkillBundleError(
                f"GitHub contents API returned unexpected payload for {ref.owner}/{ref.repo}/{current_path}@{ref.branch}"
            )

        for item in payload:
            item_type = item.get("type")
            item_path = item.get("path")
            if not isinstance(item_path, str) or not item_path:
                continue
            if item_type == "dir":
                queue.append(item_path)
                continue
            if item_type != "file":
                continue
            file_api_url = item.get("url")
            if not isinstance(file_api_url, str) or not file_api_url:
                raise FetchSkillBundleError(
                    f"GitHub contents API missing file url for {ref.owner}/{ref.repo}/{item_path}@{ref.branch}"
                )
            try:
                file_response = requests.get(file_api_url, headers=_github_api_headers(), timeout=timeout)
                file_response.raise_for_status()
                file_payload = file_response.json()
            except Exception as exc:
                raise FetchSkillBundleError(
                    f"GitHub file content request failed for {file_api_url}"
                ) from exc
            encoded_content = file_payload.get("content")
            encoding = file_payload.get("encoding")
            if not isinstance(encoded_content, str) or encoding != "base64":
                raise FetchSkillBundleError(
                    f"GitHub file content payload invalid for {ref.owner}/{ref.repo}/{item_path}@{ref.branch}"
                )
            try:
                content = base64.b64decode(encoded_content).decode("utf-8", errors="ignore")
            except Exception as exc:
                raise FetchSkillBundleError(
                    f"GitHub file content decode failed for {ref.owner}/{ref.repo}/{item_path}@{ref.branch}"
                ) from exc
            relative_path = PurePosixPath(item_path).relative_to(root_path).as_posix()
            files.append({"path": relative_path, "content": content})
    return files


def _fetch_via_github_html_pages(
    ref: GitHubTreeRef,
    timeout: int,
    *,
    requests_get: Callable[..., Any] = requests.get,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    root_path = PurePosixPath(ref.path)
    queue = [ref.path]
    files: list[dict[str, Any]] = []

    while queue:
        current_path = queue.pop(0)
        tree_url = f"https://github.com/{ref.owner}/{ref.repo}/tree/{ref.branch}/{current_path}"
        try:
            response = _http_get_with_retries(
                tree_url,
                headers={"User-Agent": GITHUB_API_HEADERS["User-Agent"]},
                timeout=timeout,
                requests_get=requests_get,
                sleep_fn=sleep_fn,
            )
            response.raise_for_status()
            tree_payload = _extract_react_embedded_data(response.text)
            items = tree_payload["payload"]["codeViewTreeRoute"]["tree"]["items"]
        except Exception as exc:
            raise FetchSkillBundleError(
                f"GitHub HTML tree request failed for {ref.owner}/{ref.repo}/{current_path}@{ref.branch}"
            ) from exc
        if not isinstance(items, list):
            raise FetchSkillBundleError(
                f"GitHub HTML tree payload invalid for {ref.owner}/{ref.repo}/{current_path}@{ref.branch}"
            )

        for item in items:
            item_path = item.get("path")
            item_type = item.get("contentType")
            if not isinstance(item_path, str) or not item_path:
                continue
            if item_type == "directory":
                queue.append(item_path)
                continue
            if item_type != "file" or not item_path.endswith(".md"):
                continue
            blob_url = f"https://github.com/{ref.owner}/{ref.repo}/blob/{ref.branch}/{item_path}"
            try:
                blob_response = _http_get_with_retries(
                    blob_url,
                    headers={"User-Agent": GITHUB_API_HEADERS["User-Agent"]},
                    timeout=timeout,
                    requests_get=requests_get,
                    sleep_fn=sleep_fn,
                )
                blob_response.raise_for_status()
                blob_payload = _extract_react_embedded_data(blob_response.text)
                rich_text = blob_payload["payload"]["codeViewBlobRoute"]["richText"]
            except Exception as exc:
                raise FetchSkillBundleError(
                    f"GitHub HTML blob request failed for {ref.owner}/{ref.repo}/{item_path}@{ref.branch}"
                ) from exc
            if not isinstance(rich_text, str):
                raise FetchSkillBundleError(
                    f"GitHub HTML blob payload invalid for {ref.owner}/{ref.repo}/{item_path}@{ref.branch}"
                )
            relative_path = PurePosixPath(item_path).relative_to(root_path).as_posix()
            files.append({"path": relative_path, "content": _rich_text_html_to_text(rich_text)})
    return files


def _default_fallback_fetch(ref: GitHubTreeRef, timeout: int) -> list[dict[str, Any]]:
    try:
        return _fetch_via_github_contents_api(ref, timeout)
    except FetchSkillBundleError:
        try:
            return _fetch_via_github_html_pages(ref, timeout)
        except FetchSkillBundleError:
            return _fetch_via_github_sparse_checkout(ref, timeout)


def fetch_skill_directory_files(
    scraper: Any,
    ref: GitHubTreeRef,
    *,
    base_url: str = SKILLSMP_GITHUB_CONTENTS_URL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    sleep_fn: Any = time.sleep,
    fallback_fetch_fn: Callable[[GitHubTreeRef, int], list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    query = urlencode(
        {
            "owner": ref.owner,
            "repo": ref.repo,
            "path": ref.path,
            "branch": ref.branch,
        }
    )
    url = f"{base_url}?{query}"
    last_status: int | None = None
    fallback = fallback_fetch_fn or _default_fallback_fetch
    for attempt in range(max_retries + 1):
        response = scraper.get(url, timeout=timeout)
        last_status = response.status_code
        if response.status_code == 429 and attempt < max_retries:
            sleep_fn(_compute_retry_delay(response.headers, attempt))
            continue
        if response.status_code == 429:
            raise FetchSkillBundleError(
                f"github-contents rate limited after {max_retries} retries, last status {response.status_code}"
            )
        if response.status_code == 403:
            return fallback(ref, timeout)
        try:
            response.raise_for_status()
        except Exception as exc:
            raise FetchSkillBundleError(
                f"github-contents request failed with status {response.status_code}"
            ) from exc
        try:
            payload = response.json()
        except Exception as exc:
            raise FetchSkillBundleError(
                f"github-contents response is not valid JSON: {exc}"
            ) from exc
        files = payload.get("files")
        if not isinstance(files, list):
            raise FetchSkillBundleError(f"Invalid github-contents payload: {payload}")
        return files
    raise FetchSkillBundleError(f"github-contents failed after retries, last status {last_status}")
