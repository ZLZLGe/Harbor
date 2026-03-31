"""Helper utilities for the Top50 bucketized search entry point."""

from __future__ import annotations

import os
import shutil
import sys

from argparse import ArgumentParser, Namespace
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from top50_search.src import evaluate_harbor_fit, fetch_skill_bundle, search_skillsmp
DEFAULT_CONFIG_PATH = ROOT / "configs/domains_and_buckets.yaml"
DEFAULT_RESULTS_ROOT = ROOT / "results"
DEFAULT_DOWNLOAD_ROOT = ROOT / "downloads"
DEFAULT_BUCKET_SLUG = "data-quality"
AUTH_TOKEN_ENV_VARS = ("SKILLSMP_API_KEY", "SKILLSMP_TOKEN", "SKILLSMP_AUTH_TOKEN")


def parse_args(argv: list[str] | None = None) -> Namespace:
    """Parse CLI arguments for a single bucket search."""

    parser = ArgumentParser(description="Run a Top50 bucket search flow.")
    parser.add_argument(
        "--config-path",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to domains_and_buckets.yaml",
    )
    parser.add_argument(
        "--bucket-slug",
        type=str,
        default=DEFAULT_BUCKET_SLUG,
        help="Slug of the bucket that should drive this search.",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=DEFAULT_RESULTS_ROOT,
        help="Directory where selected skill bundles are materialized.",
    )
    return parser.parse_args(argv)


def select_bucket_config(config_path: Path | str, bucket_slug: str) -> dict[str, Any]:
    """Load the config file and return the matching bucket entry."""

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    raw_config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw_config is None:
        raw_config = {}
    if not isinstance(raw_config, Mapping):
        raise ValueError("config must define a top-level mapping")
    buckets = raw_config.get("search_buckets")
    if not isinstance(buckets, list):
        raise ValueError("search_buckets must be a list in the config")
    for entry in buckets:
        if isinstance(entry, Mapping) and entry.get("slug") == bucket_slug:
            return dict(entry)
    raise ValueError(f"bucket slug not found in config: {bucket_slug}")


def _normalize_entry(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _sanitize_segment(value: Any, label: str) -> str:
    raw_value = str(value).strip()
    if not raw_value:
        raise ValueError(f"{label} cannot be empty")
    if "/" in raw_value or "\\" in raw_value:
        raise ValueError(f"unsafe characters detected in {label}: {raw_value}")
    posix_path = PurePosixPath(raw_value)
    if posix_path.is_absolute():
        raise ValueError(f"unsafe {label}: absolute path not allowed: {raw_value}")
    if len(posix_path.parts) != 1 or any(part in ("", ".", "..") for part in posix_path.parts):
        raise ValueError(f"unsafe {label}: {raw_value}")
    return posix_path.name


def _sanitize_rank(value: Any) -> int:
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"rank must be an integer: {value}")
    if candidate <= 0:
        raise ValueError(f"rank must be positive: {candidate}")
    return candidate


def materialize_selected_results(
    selected: Sequence[Mapping[str, Any]],
    results_root: Path | str,
    bucket_slug: str | None = None,
) -> list[dict[str, Any]]:
    """
    Copy selected skill bundles into a results bucket directory and write the manifest.
    """

    bucket = bucket_slug or DEFAULT_BUCKET_SLUG
    safe_bucket = _sanitize_segment(bucket, "bucket_slug")
    root = Path(results_root)
    target_bucket_dir = root / safe_bucket
    if target_bucket_dir.exists():
        shutil.rmtree(target_bucket_dir)
    target_bucket_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    for record in selected:
        rank = record.get("rank")
        if rank is None:
            raise ValueError("each selected record must include a rank")
        safe_rank = _sanitize_rank(rank)
        skill_id = record.get("id") or record.get("skill_id")
        if not skill_id:
            raise ValueError("each selected record must include an id")
        bundle_path = record.get("bundle_path") or record.get("bundle_dir")
        if not bundle_path:
            raise ValueError("each selected record must include a bundle_path")
        bundle_source = Path(bundle_path)
        if not bundle_source.exists():
            raise FileNotFoundError(f"bundle source missing: {bundle_source}")
        safe_skill_id = _sanitize_segment(skill_id, "skill id")
        rank_segment = f"{safe_rank:02d}"
        destination = target_bucket_dir / f"{rank_segment}__{safe_skill_id}"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(bundle_source, destination)
        entry = {
            "rank": safe_rank,
            "id": skill_id,
            "name": _normalize_entry(record.get("name")),
            "author": _normalize_entry(record.get("author")),
            "skillsmp_url": _normalize_entry(record.get("skillsmp_url")),
            "github_url": _normalize_entry(record.get("github_url")),
            "selected_dir": destination.name,
        }
        manifest.append(entry)

    manifest_path = target_bucket_dir / "selected_manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return manifest


class MissingAuthTokenError(ValueError):
    """Raised when a SkillsMP auth token cannot be resolved."""


def _clean_token(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _resolve_auth_token(bucket: dict[str, Any]) -> str:
    for env_var in AUTH_TOKEN_ENV_VARS:
        token = _clean_token(os.environ.get(env_var))
        if token:
            return token
    for key in ("auth_token", "api_key"):
        token = _clean_token(bucket.get(key))
        if token:
            return token
    env_list = ", ".join(AUTH_TOKEN_ENV_VARS)
    raise MissingAuthTokenError(
        f"SkillsMP auth token missing; set one of {env_list} or provide auth_token/api_key in the bucket config."
    )


def _assign_candidate_ranks(candidates: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        entry = dict(candidate)
        entry["rank"] = index
        ranked.append(entry)
    return ranked


def _extract_github_tree_url(candidate: dict[str, Any]) -> str:
    for key in ("github_tree_url", "github_url"):
        raw_value = candidate.get(key)
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value
    raise ValueError("candidate missing GitHub tree URL in github_tree_url or github_url")


def _build_scraper(factory: Callable[[], Any] | None) -> Any:
    if factory is not None:
        return factory()
    return requests.Session()


def _prepare_download_bucket_dir(download_root: Path | str, bucket_slug: str) -> Path:
    safe_bucket = _sanitize_segment(bucket_slug, "bucket_slug")
    download_root_path = Path(download_root)
    target_bucket_dir = download_root_path / safe_bucket
    if target_bucket_dir.exists():
        shutil.rmtree(target_bucket_dir)
    target_bucket_dir.mkdir(parents=True, exist_ok=True)
    return target_bucket_dir


def run_bucket_flow(
    bucket_slug: str,
    bucket_config: dict[str, Any],
    *,
    download_root: Path | str = DEFAULT_DOWNLOAD_ROOT,
    results_root: Path | str = DEFAULT_RESULTS_ROOT,
    search_scraper_factory: Callable[[], Any] | None = None,
    fetch_scraper_factory: Callable[[], Any] | None = None,
    search_fn: Callable[[Any, dict[str, Any]], list[dict[str, Any]]] = search_skillsmp.search_bucket_candidates,
    parse_tree_fn: Callable[[str], fetch_skill_bundle.GitHubTreeRef] = fetch_skill_bundle.parse_github_tree_url,
    fetch_files_fn: Callable[[Any, fetch_skill_bundle.GitHubTreeRef], list[dict[str, Any]]] = fetch_skill_bundle.fetch_skill_directory_files,
    write_files_fn: Callable[[list[dict[str, Any]], Path | str], list[Path]] = fetch_skill_bundle.write_downloaded_skill_files,
    evaluate_fn: Callable[[Path | str], dict[str, Any]] = evaluate_harbor_fit.evaluate_skill_bundle,
    materialize_fn: Callable[[Sequence[Mapping[str, Any]], Path | str, str | None], list[dict[str, Any]]] = materialize_selected_results,
) -> list[dict[str, Any]]:
    """
    Run the bucket search pipeline for a single bucket.
    """

    token = _resolve_auth_token(bucket_config)
    search_config = dict(bucket_config)
    search_config["auth_token"] = token

    search_scraper = _build_scraper(search_scraper_factory)
    candidates = search_fn(search_scraper, search_config)
    ranked = _assign_candidate_ranks(candidates)

    fetch_scraper = _build_scraper(fetch_scraper_factory)
    download_root_path = Path(download_root)
    _prepare_download_bucket_dir(download_root_path, bucket_slug)
    results_root_path = Path(results_root)
    processed: list[dict[str, Any]] = []
    for candidate in ranked:
        try:
            tree_url = _extract_github_tree_url(candidate)
            ref = parse_tree_fn(tree_url)
            files = fetch_files_fn(fetch_scraper, ref)
            bundle_dir = fetch_skill_bundle.build_candidate_download_dir(download_root_path, bucket_slug, candidate)
            write_files_fn(files, bundle_dir)
            evaluation = evaluate_fn(bundle_dir)
        except (fetch_skill_bundle.FetchSkillBundleError, FileNotFoundError, ValueError) as exc:
            skill_id = candidate.get("id") or candidate.get("name") or "<unknown>"
            print(f"skip candidate {skill_id}: {exc}")
            continue
        record = dict(candidate)
        record["bundle_path"] = str(bundle_dir)
        record["evaluation"] = evaluation
        processed.append(record)

    selected = [
        record for record in processed if record.get("evaluation", {}).get("selected")
    ]
    return materialize_fn(selected, results_root_path, bucket_slug)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        bucket_config = select_bucket_config(args.config_path, args.bucket_slug)
        manifest = run_bucket_flow(
            bucket_slug=args.bucket_slug,
            bucket_config=bucket_config,
            results_root=args.results_root,
        )
    except (
        FileNotFoundError,
        ValueError,
        MissingAuthTokenError,
        fetch_skill_bundle.FetchSkillBundleError,
        search_skillsmp.SearchSkillsMPError,
    ) as exc:
        raise SystemExit(str(exc))
    bucket_dir = Path(args.results_root) / args.bucket_slug
    manifest_path = bucket_dir / "selected_manifest.yaml"
    print(
        f"bucket {args.bucket_slug} ({bucket_config.get('domain')}) materialized {len(manifest)} selected bundle(s) at {manifest_path}"
    )


if __name__ == "__main__":
    main()
